import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.pwc_discover import discover_from_html
from utils.pwc_archive import classify_entity_type, dump_json, dump_jsonl, load_json, stable_id


def rows_from_manifest(path: Path) -> list[dict]:
    rows = load_json(path, [])
    normalized = []
    for row in rows:
        archive_url = row.get("archive_url") or row.get("discovered_url")
        if not archive_url:
            continue
        normalized.append(
            {
                "id": row.get("id") or stable_id(archive_url),
                "entity_type": row.get("entity_type") or classify_entity_type(archive_url),
                "archive_url": archive_url,
                "source": str(path),
                "status": row.get("status", "pending"),
            }
        )
    return normalized


def rows_from_seed_html(seed_dir: Path) -> list[dict]:
    rows = []
    if not seed_dir.exists():
        return rows
    for html_file in sorted(seed_dir.glob("*.html")):
        html = html_file.read_text(encoding="utf-8")
        source_url = html_file.stem.replace("seed-", "")
        for row in discover_from_html(html, source_url):
            rows.append(
                {
                    "id": row["id"],
                    "entity_type": row["entity_type"],
                    "archive_url": row["discovered_url"],
                    "source": str(html_file),
                    "status": row.get("status", "pending"),
                }
            )
    return rows


def rows_from_manual_urls(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        rows.append(
            {
                "id": stable_id(entry),
                "entity_type": classify_entity_type(entry),
                "archive_url": entry,
                "source": str(path),
                "status": "pending",
            }
        )
    return rows


def merge_rows(*groups: list[dict], limit: int | None = None) -> list[dict]:
    merged = {}
    for group in groups:
        for row in group:
            merged[row["archive_url"]] = row
    rows = list(merged.values())
    rows.sort(key=lambda item: (0 if item["entity_type"] == "paper" else 1, item["archive_url"]))
    if limit is not None:
        rows = rows[:limit]
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge local seed sources into a unified archive manifest.")
    parser.add_argument(
        "--manifest",
        action="append",
        dest="manifests",
        default=[],
        help="Existing manifest JSON file to merge. May be repeated.",
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=Path("data/pwc_archive/raw/seeds"),
        help="Directory containing cached seed HTML files.",
    )
    parser.add_argument(
        "--manual-urls",
        type=Path,
        default=Path("data/pwc_archive/staging/manual_urls.txt"),
        help="Text file containing one archive URL per line.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on merged rows.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/pwc_archive/staging/local_seed_manifest.json"),
        help="Merged manifest JSON output path.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("data/pwc_archive/raw/cdx/local_seed_manifest.jsonl"),
        help="Merged manifest JSONL output path.",
    )
    args = parser.parse_args()

    manifest_rows = []
    for manifest_path in args.manifests:
        manifest_rows.extend(rows_from_manifest(Path(manifest_path)))

    merged = merge_rows(
        manifest_rows,
        rows_from_seed_html(args.seed_dir),
        rows_from_manual_urls(args.manual_urls),
        limit=args.limit,
    )
    dump_json(args.output, merged)
    dump_jsonl(args.output_jsonl, merged)
    print(f"Wrote {len(merged)} merged local seed rows to {args.output}")


if __name__ == "__main__":
    main()
