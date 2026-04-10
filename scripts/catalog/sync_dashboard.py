"""Sync health dashboard and blocked queue monitoring."""

from datetime import datetime, timezone
from pathlib import Path

from utils.pwc_archive import load_json

from .shared import FACET_SPECS


def infer_error_kind(row: dict) -> str:
    kind = str(row.get("error_kind") or "").strip()
    if kind:
        return kind
    message = str(row.get("error", "")).lower()
    if "429" in message or "too many requests" in message:
        return "rate_limit"
    if "ssl" in message or "wrong version number" in message or "tls" in message:
        return "tls"
    if "timeout" in message or "timed out" in message or "read timed out" in message:
        return "timeout"
    return "other"


def load_sync_summary(project_root: Path) -> dict[str, int]:
    manifest = load_json(project_root / "data/pwc_archive/staging/local_seed_manifest.json", [])
    bulk_state = load_json(project_root / "data/pwc_archive/staging/bulk_sync_state.json", {})
    fetch_state = load_json(project_root / "data/pwc_archive/staging/fetch_state.json", [])
    normalized_dir = project_root / "data/pwc_archive/normalized/papers"

    normalized_files = len(list(normalized_dir.glob("*.json"))) if normalized_dir.exists() else 0
    fetched_success = sum(1 for row in fetch_state if row.get("fetch_status") in {"fetched", "cached"})
    fetch_errors = sum(1 for row in fetch_state if row.get("fetch_status") == "error")
    rate_limited = sum(1 for row in fetch_state if row.get("fetch_status") == "error" and infer_error_kind(row) == "rate_limit")
    tls_total = sum(1 for row in fetch_state if row.get("fetch_status") == "error" and infer_error_kind(row) == "tls")
    timeout_total = sum(1 for row in fetch_state if row.get("fetch_status") == "error" and infer_error_kind(row) == "timeout")
    other_error_total = sum(
        1 for row in fetch_state if row.get("fetch_status") == "error" and infer_error_kind(row) not in {"rate_limit", "tls", "timeout"}
    )
    pending = max(len(manifest) - fetched_success - fetch_errors, 0)

    return {
        "seed_total": len(manifest),
        "fetched_success": fetched_success,
        "fetch_errors": fetch_errors,
        "rate_limited": rate_limited,
        "tls_total": tls_total or int(bulk_state.get("tls_total", 0) or 0),
        "timeout_total": timeout_total or int(bulk_state.get("timeout_total", 0) or 0),
        "other_error_total": other_error_total or int(bulk_state.get("other_error_total", 0) or 0),
        "pending": pending,
        "normalized_files": normalized_files,
    }


def load_blocked_sync_rows(project_root: Path, limit: int = 6) -> list[dict]:
    fetch_state = load_json(project_root / "data/pwc_archive/staging/fetch_state.json", [])
    rows = []
    for row in fetch_state:
        if row.get("fetch_status") != "error":
            continue
        rows.append(row)
    rows.sort(key=lambda row: float(row.get("retry_after_epoch") or 0), reverse=False)
    return rows[:limit]


def next_retry_epoch(project_root: Path) -> float | None:
    fetch_state = load_json(project_root / "data/pwc_archive/staging/fetch_state.json", [])
    retry_epochs = [
        float(row.get("retry_after_epoch"))
        for row in fetch_state
        if row.get("fetch_status") == "error" and row.get("retry_after_epoch")
    ]
    return min(retry_epochs) if retry_epochs else None


def retry_label(epoch: float | int | None) -> str:
    if not epoch:
        return "Retry window unknown"
    retry_at = datetime.fromtimestamp(float(epoch), tz=timezone.utc).astimezone()
    now = datetime.now(retry_at.tzinfo)
    delta_seconds = int((retry_at - now).total_seconds())
    if delta_seconds <= 0:
        return "Ready to retry now"
    minutes = max(delta_seconds // 60, 1)
    if minutes < 60:
        return f"Retry in about {minutes} min"
    hours = max(minutes // 60, 1)
    return f"Retry in about {hours} hr"


def retry_schedule_label(epoch: float | int | None) -> str:
    if not epoch:
        return "No retry window scheduled"
    retry_at = datetime.fromtimestamp(float(epoch), tz=timezone.utc).astimezone()
    now = datetime.now(retry_at.tzinfo)
    delta_seconds = int((retry_at - now).total_seconds())
    stamp = retry_at.strftime("%Y-%m-%d %H:%M")
    if delta_seconds <= 0:
        return f"Ready now. Suggested rerun: {stamp}"
    minutes = max(delta_seconds // 60, 1)
    if minutes < 60:
        return f"Suggested rerun in about {minutes} min, around {stamp}"
    hours = max(minutes // 60, 1)
    return f"Suggested rerun in about {hours} hr, around {stamp}"


def blocked_error_label(error: str) -> str:
    message = (error or "").lower()
    if "429" in message:
        return "Wayback 429"
    if "ssl" in message:
        return "TLS handshake"
    if "timeout" in message:
        return "Timeout"
    return "Fetch error"


def blocked_entity_counts(rows: list[dict]) -> list[tuple[str, int]]:
    preferred = ["paper", "task", "method", "dataset"]
    counts: dict[str, int] = {}
    for row in rows:
        entity_type = str(row.get("entity_type") or "item").strip().lower()
        counts[entity_type] = counts.get(entity_type, 0) + 1

    ordered = [(entity_type, counts[entity_type]) for entity_type in preferred if entity_type in counts]
    extras = sorted(
        [(entity_type, count) for entity_type, count in counts.items() if entity_type not in preferred],
        key=lambda item: item[0],
    )
    return ordered + extras


def render_blocked_sync_list(rows: list[dict]) -> str:
    if not rows:
        return "<article class='archive-empty-state'><h3>No blocked URLs</h3><p>The current sync queue does not have any archived pages waiting on a retry window.</p></article>"

    filters = [
        "<button class='archive-filter-pill is-active' type='button' data-blocked-filter='all'>All blockers</button>"
    ]
    for entity_type, count in blocked_entity_counts(rows):
        filters.append(
            f"<button class='archive-filter-pill' type='button' data-blocked-filter='{entity_type}'>{entity_type.title()} <strong>{count}</strong></button>"
        )
    status_filters = [
        "<button class='archive-filter-pill is-active' type='button' data-blocked-status='all' data-blocked-status-label='All windows'>All windows</button>",
        "<button class='archive-filter-pill' type='button' data-blocked-status='ready' data-blocked-status-label='Only ready now'>Only ready now</button>",
        "<button class='archive-filter-pill' type='button' data-blocked-status='cooling' data-blocked-status-label='Cooling down'>Cooling down</button>",
    ]

    items = []
    for row in rows:
        archive_url = row.get("archive_url", "")
        entity_type = row.get("entity_type", "item")
        label = archive_url.rstrip("/").split("/")[-1] or entity_type
        retry_epoch = row.get("retry_after_epoch") or ""
        items.append(
            f"<li data-blocked-entity='{entity_type}' data-blocked-retry-epoch='{retry_epoch}'>"
            f"<div><strong>{label}</strong><span>{blocked_error_label(str(row.get('error', '')))} · {entity_type}</span></div>"
            f"<em>{retry_label(row.get('retry_after_epoch'))}</em>"
            "</li>"
        )
    return "\n".join(
        [
            "<article class='section-card archive-blocked-card' data-blocked-filter-group>",
            "  <h3>Blocked sync queue</h3>",
            "  <p>These archived URLs are currently waiting for the next retry window, so the ingest worker will skip them until they cool down.</p>",
            "  <div class='archive-filter-bar'>",
            *filters,
            "  </div>",
            "  <div class='archive-filter-bar archive-filter-bar--status'>",
            *status_filters,
            "  </div>",
            "  <ul class='archive-blocked-list'>",
            *items,
            "  </ul>",
            "</article>",
        ]
    )


def render_retry_glance(sync: dict[str, int], blocked_rows: list[dict], next_retry: float | None) -> str:
    priority_labels = []
    for row in blocked_rows[:3]:
        archive_url = row.get("archive_url", "")
        label = archive_url.rstrip("/").split("/")[-1] or row.get("entity_type", "item")
        priority_labels.append(f"<span>{label}</span>")
    if not priority_labels:
        priority_labels.append("<span>No blocked URLs</span>")

    return "\n".join(
        [
            "<article class='archive-retry-glance'>",
            "  <span class='archive-retry-glance__eyebrow'>Next sync window</span>",
            f"  <strong>{retry_schedule_label(next_retry)}</strong>",
            "  <p>The worker will skip cooled-down failures automatically, so the best next move is to rerun after this window instead of hammering the same archived pages.</p>",
            "  <div class='archive-retry-glance__pills'>",
            *priority_labels,
            "  </div>",
            "  <div class='archive-retry-glance__actions'>",
            "    <code>python scripts/pwc_bulk_sync.py --batch-size 3 --max-batches 4 --wait-between-batches 30</code>",
            "  </div>",
            "</article>",
            "<div class='archive-retry-breakdown'>",
            "  <article>",
            "    <span>Rate-limited</span>",
            f"    <strong>{sync['rate_limited']}</strong>",
            "    <p>Wayback 429 responses currently dominating the blocked queue.</p>",
            "  </article>",
            "  <article>",
            "    <span>TLS failures</span>",
            f"    <strong>{sync['tls_total']}</strong>",
            "    <p>Handshake failures that usually recover with a shorter cool-down.</p>",
            "  </article>",
            "  <article>",
            "    <span>Timeouts</span>",
            f"    <strong>{sync['timeout_total']}</strong>",
            "    <p>Slow responses that should be retried in the next batch window.</p>",
            "  </article>",
            "  <article>",
            "    <span>Pending queue</span>",
            f"    <strong>{sync['pending']}</strong>",
            "    <p>Seeds that still have not been fetched into the normalized ingest lane.</p>",
            "  </article>",
            "</div>",
        ]
    )
