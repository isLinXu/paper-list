import argparse
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.pwc_discover import discover_from_html
from scripts.pwc_fetch_archive import fetch_archive_html
from utils.pwc_archive import dump_json, dump_jsonl, stable_id


def cached_seed_path(output_dir: Path, archive_url: str) -> Path:
    return output_dir / f"seed-{stable_id(archive_url)}.html"


def build_seed_rows(
    archive_urls: list[str],
    output_dir: Path,
    limit: int | None = None,
    continue_on_error: bool = False,
    max_retries: int = 3,
    use_cache: bool = True,
) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict] = {}

    for archive_url in archive_urls:
        seed_path = cached_seed_path(output_dir, archive_url)
        try:
            if use_cache and seed_path.exists():
                html = seed_path.read_text(encoding="utf-8")
                final_url = archive_url
            else:
                html, final_url = fetch_archive_html(archive_url, max_retries=max_retries)
                seed_path.write_text(html, encoding="utf-8")
        except requests.RequestException:
            if continue_on_error:
                continue
            raise
        for row in discover_from_html(html, final_url):
            normalized = {
                "id": row["id"],
                "entity_type": row["entity_type"],
                "archive_url": row["discovered_url"],
                "source_archive_url": final_url,
                "status": row.get("status", "pending"),
            }
            merged[normalized["archive_url"]] = normalized

    manifest = list(merged.values())
    manifest.sort(key=lambda item: (0 if item["entity_type"] == "paper" else 1, item["archive_url"]))
    if limit is not None:
        manifest = manifest[:limit]
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a manifest from archived PapersWithCode entry pages.")
    parser.add_argument(
        "--archive-url",
        action="append",
        dest="archive_urls",
        required=True,
        help="Archived page URL to inspect. Provide multiple times to merge sources.",
    )
    parser.add_argument(
        "--raw-output-dir",
        type=Path,
        default=Path("data/pwc_archive/raw/seeds"),
        help="Directory for fetched seed snapshot HTML files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/pwc_archive/staging/seed_manifest.json"),
        help="Manifest JSON output path.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("data/pwc_archive/raw/cdx/seed_manifest.jsonl"),
        help="Manifest JSONL output path.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on discovered rows.")
    parser.add_argument("--continue-on-error", action="store_true", help="Skip seed pages that fail to fetch.")
    parser.add_argument("--max-retries", type=int, default=3, help="Retry count for fetching each seed page.")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached seed HTML files and refetch from Wayback.")
    args = parser.parse_args()

    rows = build_seed_rows(
        args.archive_urls,
        args.raw_output_dir,
        args.limit,
        args.continue_on_error,
        args.max_retries,
        use_cache=not args.no_cache,
    )
    dump_json(args.output, rows)
    dump_jsonl(args.output_jsonl, rows)
    print(f"Wrote {len(rows)} seed rows to {args.output}")


if __name__ == "__main__":
    main()
