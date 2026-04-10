import argparse
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pwc_archive import dump_json, dump_jsonl, stable_id


DEFAULT_PATHS = ["/paper/*", "/task/*", "/method/*", "/dataset/*"]


def fetch_cdx_rows(
    base_url: str,
    path_pattern: str,
    from_timestamp: str | None = None,
    to_timestamp: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    params = {
        "url": f"https://paperswithcode.com{path_pattern}",
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype",
        "filter": ["statuscode:200", "mimetype:text/html"],
        "collapse": "urlkey",
    }
    if limit is not None:
        params["limit"] = str(limit)
    if from_timestamp:
        params["from"] = from_timestamp
    if to_timestamp:
        params["to"] = to_timestamp
    response = requests.get(base_url, params=params, timeout=30, headers={"User-Agent": "paper-list/1.0"})
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return []
    header, *body = rows
    result = []
    for values in body:
        result.append(dict(zip(header, values)))
    return result


def build_manifest(cdx_rows: list[dict]) -> list[dict]:
    manifest = []
    for row in cdx_rows:
        original = row["original"]
        entity_type = "unknown"
        for kind in ("paper", "task", "method", "dataset"):
            if f"/{kind}/" in original:
                entity_type = kind
                break
        archive_url = f"https://web.archive.org/web/{row['timestamp']}/{original}"
        manifest.append(
            {
                "id": stable_id(row["timestamp"], original),
                "entity_type": entity_type,
                "original_url": original,
                "archive_url": archive_url,
                "capture_timestamp": row["timestamp"],
                "status": "pending",
            }
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover archived PapersWithCode entities from the Wayback CDX API.")
    parser.add_argument(
        "--cdx-base-url",
        default="https://web.archive.org/cdx/search/cdx",
        help="CDX API base URL.",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=[],
        help="Additional path pattern to query, for example /paper/*.",
    )
    parser.add_argument("--from-timestamp", default=None, help="Inclusive CDX lower bound, e.g. 20250101.")
    parser.add_argument("--to-timestamp", default=None, help="Inclusive CDX upper bound, e.g. 20251231.")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on manifest size after deduplication.")
    parser.add_argument("--timeout", type=int, default=30, help="Per-request timeout in seconds.")
    parser.add_argument("--continue-on-error", action="store_true", help="Skip path patterns that time out or fail.")
    parser.add_argument(
        "--state-output",
        type=Path,
        default=Path("data/pwc_archive/staging/cdx_state.json"),
        help="Per-path CDX state output path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/pwc_archive/staging/cdx_manifest.json"),
        help="JSON manifest output path.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("data/pwc_archive/raw/cdx/cdx_manifest.jsonl"),
        help="JSONL output path.",
    )
    args = parser.parse_args()

    paths = args.paths or DEFAULT_PATHS
    rows: list[dict] = []
    state_rows: list[dict] = []
    for path_pattern in paths:
        per_path_limit = args.limit if args.limit is not None else None
        try:
            path_rows = fetch_cdx_rows(
                args.cdx_base_url,
                path_pattern,
                args.from_timestamp,
                args.to_timestamp,
                per_path_limit,
            )
            rows.extend(path_rows)
            state_rows.append({"path": path_pattern, "status": "ok", "count": len(path_rows)})
        except requests.RequestException as exc:
            state_rows.append({"path": path_pattern, "status": "error", "error": str(exc)})
            if not args.continue_on_error:
                raise

    deduped = {}
    for item in build_manifest(rows):
        deduped[item["archive_url"]] = item

    manifest = list(deduped.values())
    manifest.sort(key=lambda item: item["capture_timestamp"], reverse=True)
    if args.limit is not None:
        manifest = manifest[: args.limit]
    dump_json(args.output, manifest)
    dump_jsonl(args.output_jsonl, manifest)
    dump_json(args.state_output, state_rows)
    print(f"Wrote {len(manifest)} archive candidates to {args.output}")


if __name__ == "__main__":
    main()
