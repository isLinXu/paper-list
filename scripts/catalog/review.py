"""Review queue logic: flag, prioritize, and suggest actions for records needing attention."""

from datetime import datetime, timezone


def capture_age_days(record: dict) -> int | None:
    stamp = record.get("capture_timestamp")
    if not stamp:
        return None
    try:
        captured = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    return max(0, (now - captured).days)


def review_reasons(record: dict) -> list[str]:
    reasons = []
    confidence = record.get("confidence") or {}
    paper_match = confidence.get("paper_match")
    repo_match = confidence.get("repo_match")
    provenance_count = len(record.get("source_provenance") or [])
    age_days = capture_age_days(record)
    if paper_match is None or float(paper_match) < 0.8:
        reasons.append("Low paper confidence")
    if record.get("repo_url") and (repo_match is None or float(repo_match) < 0.9):
        reasons.append("Low repo confidence")
    if not record.get("venue"):
        reasons.append("Missing venue")
    if not record.get("datasets"):
        reasons.append("Missing datasets")
    if not record.get("benchmarks"):
        reasons.append("Missing benchmarks")
    if not record.get("repo_topics"):
        reasons.append("Missing repo topics")
    if not record.get("frameworks"):
        reasons.append("Missing frameworks")
    if provenance_count < 2:
        reasons.append("Sparse provenance")
    if age_days is not None and age_days > 240:
        reasons.append("Stale archive snapshot")
    return reasons


def review_candidates(records: list[dict]) -> list[tuple[dict, list[str]]]:
    ranked = []
    for record in records:
        reasons = review_reasons(record)
        if reasons:
            ranked.append((record, reasons))
    ranked.sort(
        key=lambda item: (
            -len(item[1]),
            float((item[0].get("confidence") or {}).get("paper_match") or 0),
            str(item[0].get("title") or "").lower(),
        )
    )
    return ranked


def review_priority(record: dict, reasons: list[str]) -> str:
    confidence = record.get("confidence") or {}
    paper_match = float(confidence.get("paper_match") or 0)
    repo_match = float(confidence.get("repo_match") or 0)
    if "Low paper confidence" in reasons or "Low repo confidence" in reasons:
        return "High"
    if "Stale archive snapshot" in reasons and "Sparse provenance" in reasons:
        return "High"
    if len(reasons) >= 4:
        return "High"
    if len(reasons) >= 2 or paper_match < 0.92 or (record.get("repo_url") and repo_match < 0.95):
        return "Medium"
    return "Low"


def review_actions(record: dict, reasons: list[str]) -> list[str]:
    actions = []
    provenance_sources = {item.get("source") for item in record.get("source_provenance") or []}
    github_needed = any(
        reason in reasons
        for reason in ["Low repo confidence", "Missing repo topics", "Missing datasets", "Missing benchmarks", "Missing frameworks"]
    )
    if "Missing venue" in reasons and "openalex" in provenance_sources:
        actions.append("Re-run OpenAlex enrichment and verify venue mapping.")
    elif "Missing venue" in reasons:
        actions.append("Prioritize bibliographic enrichment to recover venue metadata.")

    if "Low paper confidence" in reasons:
        actions.append("Check archived paper page against DOI/arXiv title and author match.")
    if "Low repo confidence" in reasons:
        actions.append("Verify the linked repository is the intended implementation before keeping it.")
    if "Missing repo topics" in reasons:
        actions.append("Refresh GitHub enrichment to pull repository topics and homepage hints.")
    if github_needed:
        actions.append("Configure GITHUB_TOKEN before rerunning GitHub enrichment if the unauthenticated API starts rate-limiting.")
    if "Missing datasets" in reasons or "Missing benchmarks" in reasons:
        actions.append("Inspect README and archived task pages for dataset or benchmark mentions.")
    if "Missing frameworks" in reasons:
        actions.append("Review README, requirements, or language mix to recover framework labels.")
    if "Sparse provenance" in reasons:
        actions.append("Add another independent source link before trusting the record as stable.")
    if "Stale archive snapshot" in reasons:
        actions.append("Refresh the archive-backed evidence or confirm the snapshot is still representative.")

    deduped = []
    seen = set()
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        deduped.append(action)
    return deduped[:4]


def review_commands(record: dict, reasons: list[str]) -> list[str]:
    source_file = record.get("_source_file")
    commands = []
    rebuild_command = "python scripts/pwc_build_catalog.py"
    github_needed = any(
        reason in reasons
        for reason in ["Low repo confidence", "Missing repo topics", "Missing datasets", "Missing benchmarks", "Missing frameworks"]
    )
    if source_file:
        if "Missing venue" in reasons or "Low paper confidence" in reasons:
            commands.append(f"python scripts/pwc_enrich_openalex.py --input {source_file}")
        if github_needed:
            commands.append(f"python scripts/pwc_enrich_github.py --input {source_file}")
            commands.append("export GITHUB_TOKEN=your_token_here")
        if "Sparse provenance" in reasons or "Stale archive snapshot" in reasons:
            commands.append(f"python scripts/pwc_seed_from_archive.py --archive-url {record.get('archive_page_url', '')} --limit 5")
    commands.append(rebuild_command)

    deduped = []
    seen = set()
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped.append(command)
    deduped = [command for command in deduped if command != rebuild_command][:4]
    deduped.append(rebuild_command)
    return deduped


def review_reason_counts(records: list[dict], limit: int = 5) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for record, reasons in review_candidates(records):
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    return ranked[:limit]
