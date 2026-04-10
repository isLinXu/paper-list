import argparse
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pwc_archive import classify_entity_type, dump_json, dump_jsonl, extract_links, resolve_archive_link, stable_id

# Backward-compatible alias: other scripts may import ``classify`` from here.
classify = classify_entity_type


def discover_from_html(html: str, source_url: str) -> list[dict]:
    rows = []
    for link in extract_links(html):
        if link.startswith("/"):
            link = resolve_archive_link(source_url, link)
        if "/paper/" not in link and "/task/" not in link and "/method/" not in link and "/dataset/" not in link:
            continue
        rows.append(
            {
                "id": stable_id(source_url, link),
                "source_url": source_url,
                "discovered_url": link,
                "entity_type": classify_entity_type(link),
                "status": "pending",
            }
        )
    deduped = {}
    for row in rows:
        deduped[row["discovered_url"]] = row
    return list(deduped.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover PapersWithCode archive entity URLs from archived HTML.")
    parser.add_argument("--input-html", type=Path, required=True, help="Local archived HTML snapshot to scan.")
    parser.add_argument("--source-url", required=True, help="Archived page URL corresponding to the HTML snapshot.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/pwc_archive/staging/discovery_manifest.json"),
        help="Discovery manifest output path.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("data/pwc_archive/raw/cdx/discovery_manifest.jsonl"),
        help="JSONL output path for append-friendly processing.",
    )
    args = parser.parse_args()

    html = args.input_html.read_text(encoding="utf-8")
    rows = discover_from_html(html, args.source_url)
    dump_json(args.output, rows)
    dump_jsonl(args.output_jsonl, rows)
    print(f"Discovered {len(rows)} archive URLs from {args.input_html}")


if __name__ == "__main__":
    main()
