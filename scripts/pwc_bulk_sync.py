import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pwc_fetch_archive import fetch_archive_html
from utils.pwc_archive import dump_json, load_json, manifest_row_filename


def load_rows(path: Path) -> list[dict]:
    return load_json(path, []) if path.exists() else []


def classify_fetch_error(error: str) -> str:
    message = (error or "").lower()
    if "429" in message or "too many requests" in message:
        return "rate_limit"
    if "ssl" in message or "wrong version number" in message or "tls" in message:
        return "tls"
    if "timeout" in message or "timed out" in message or "read timed out" in message:
        return "timeout"
    return "other"


def row_error_kind(row: dict) -> str:
    kind = row.get("error_kind")
    if kind:
        return kind
    return classify_fetch_error(str(row.get("error", "")))


def cooldown_for_error(error: str, default_cooldown_seconds: int) -> int:
    kind = classify_fetch_error(error)
    if kind == "rate_limit":
        return default_cooldown_seconds
    if kind == "tls":
        return min(default_cooldown_seconds, 600)
    if kind == "timeout":
        return min(default_cooldown_seconds, 900)
    return min(default_cooldown_seconds, 1200)


def build_known_sets(raw_dir: Path, normalized_dir: Path, fetch_state: list[dict]) -> tuple[set[str], set[str], dict[str, dict]]:
    fetched_urls = {row.get("archive_url") for row in fetch_state if row.get("fetch_status") in {"fetched", "cached"}}
    error_rows = {row.get("archive_url"): row for row in fetch_state if row.get("fetch_status") == "error"}

    if raw_dir.exists():
        for html_path in raw_dir.glob("*.html"):
            fetched_urls.add(html_path.stem)

    normalized_ids = set()
    if normalized_dir.exists():
        for json_path in normalized_dir.glob("*.json"):
            normalized_ids.add(json_path.stem)

    return fetched_urls, normalized_ids, error_rows


def eligible_rows(
    manifest: list[dict],
    raw_dir: Path,
    normalized_dir: Path,
    existing_state: list[dict],
    entity_type: str,
    cooldown_seconds: int,
) -> list[dict]:
    now = time.time()
    fetched_urls, normalized_ids, error_rows = build_known_sets(raw_dir, normalized_dir, existing_state)
    rows = []
    for row in manifest:
        if entity_type and row.get("entity_type") != entity_type:
            continue
        archive_url = row.get("archive_url")
        if not archive_url:
            continue
        filename = manifest_row_filename(row)
        if archive_url in fetched_urls or filename.removesuffix(".html") in normalized_ids:
            continue
        error_row = error_rows.get(archive_url)
        if error_row and cooldown_seconds > 0:
            retry_at = float(error_row.get("retry_after_epoch", 0))
            if retry_at and retry_at > now:
                continue
        rows.append(row)
    rows.sort(
        key=lambda row: (
            0 if row.get("entity_type") == "paper" else 1,
            0 if row.get("source", "").endswith("manual_urls.txt") else 1,
            row.get("archive_url", ""),
        )
    )
    return rows


def fetch_batch(rows: list[dict], output_dir: Path, sleep_seconds: float, max_retries: int, cooldown_seconds: int) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_rows = []
    for row in rows:
        try:
            html, final_url = fetch_archive_html(row["archive_url"], max_retries=max_retries)
        except Exception as exc:  # noqa: BLE001
            error_text = str(exc)
            error_kind = classify_fetch_error(error_text)
            cooldown = cooldown_for_error(error_text, cooldown_seconds)
            state_rows.append(
                {
                    **row,
                    "fetch_status": "error",
                    "error": error_text,
                    "error_kind": error_kind,
                    "last_attempt_epoch": time.time(),
                    "retry_after_epoch": time.time() + cooldown,
                }
            )
            continue

        output_path = output_dir / manifest_row_filename(row)
        output_path.write_text(html, encoding="utf-8")
        state_rows.append(
            {
                **row,
                "archive_url": final_url,
                "raw_html_path": str(output_path),
                "fetch_status": "fetched",
                "last_attempt_epoch": time.time(),
            }
        )
        time.sleep(sleep_seconds)
    return state_rows


def merge_state(existing_state: list[dict], new_state: list[dict]) -> list[dict]:
    merged = {row.get("archive_url"): row for row in existing_state if row.get("archive_url")}
    for row in new_state:
        merged[row["archive_url"]] = row
    return sorted(merged.values(), key=lambda item: (item.get("fetch_status") != "fetched", item.get("archive_url", "")))


def build_summary(manifest: list[dict], queue: list[dict], batch: list[dict], merged_state: list[dict], completed_batches: int) -> dict[str, int]:
    tls_total = sum(1 for row in merged_state if row.get("fetch_status") == "error" and row_error_kind(row) == "tls")
    timeout_total = sum(1 for row in merged_state if row.get("fetch_status") == "error" and row_error_kind(row) == "timeout")
    other_total = sum(
        1
        for row in merged_state
        if row.get("fetch_status") == "error" and row_error_kind(row) not in {"rate_limit", "tls", "timeout"}
    )
    return {
        "manifest_total": len(manifest),
        "eligible_remaining": max(len(queue) - len(batch), 0),
        "batch_attempted": len(batch),
        "completed_batches": completed_batches,
        "fetched_total": sum(1 for row in merged_state if row.get("fetch_status") in {"fetched", "cached"}),
        "error_total": sum(1 for row in merged_state if row.get("fetch_status") == "error"),
        "rate_limited_total": sum(1 for row in merged_state if row.get("fetch_status") == "error" and row_error_kind(row) == "rate_limit"),
        "tls_total": tls_total,
        "timeout_total": timeout_total,
        "other_error_total": other_total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bulk PapersWithCode archive sync in resumable batches.")
    parser.add_argument("--manifest", type=Path, default=Path("data/pwc_archive/staging/local_seed_manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/pwc_archive/raw/html"))
    parser.add_argument("--normalized-dir", type=Path, default=Path("data/pwc_archive/normalized/papers"))
    parser.add_argument("--state-output", type=Path, default=Path("data/pwc_archive/staging/fetch_state.json"))
    parser.add_argument("--summary-output", type=Path, default=Path("data/pwc_archive/staging/bulk_sync_state.json"))
    parser.add_argument("--entity-type", default="paper")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--cooldown-seconds", type=int, default=1800)
    parser.add_argument("--max-batches", type=int, default=1, help="Run multiple resumable batches in one invocation.")
    parser.add_argument(
        "--wait-between-batches",
        type=float,
        default=0.0,
        help="Optional pause between batches so long-running syncs can back off more gently.",
    )
    args = parser.parse_args()

    manifest = load_rows(args.manifest)
    existing_state = load_rows(args.state_output)
    completed_batches = 0
    queue: list[dict] = []
    batch: list[dict] = []

    for batch_index in range(max(args.max_batches, 1)):
        queue = eligible_rows(
            manifest,
            args.output_dir,
            args.normalized_dir,
            existing_state,
            args.entity_type,
            args.cooldown_seconds,
        )
        batch = queue[: args.batch_size]
        if not batch:
            break
        new_state = fetch_batch(batch, args.output_dir, args.sleep_seconds, args.max_retries, args.cooldown_seconds)
        existing_state = merge_state(existing_state, new_state)
        dump_json(args.state_output, existing_state)
        completed_batches = batch_index + 1
        if args.wait_between_batches > 0 and completed_batches < args.max_batches:
            time.sleep(args.wait_between_batches)

    merged_state = existing_state
    if not queue:
        queue = eligible_rows(
            manifest,
            args.output_dir,
            args.normalized_dir,
            merged_state,
            args.entity_type,
            args.cooldown_seconds,
        )
        batch = []

    summary = build_summary(manifest, queue, batch, merged_state, completed_batches)
    dump_json(args.summary_output, summary)
    print(
        "Bulk sync summary: "
        f"attempted={summary['batch_attempted']}, "
        f"completed_batches={summary['completed_batches']}, "
        f"fetched_total={summary['fetched_total']}, "
        f"errors={summary['error_total']}, "
        f"rate_limited={summary['rate_limited_total']}, "
        f"eligible_remaining={summary['eligible_remaining']}"
    )


if __name__ == "__main__":
    main()
