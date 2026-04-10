import argparse
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pwc_archive import dump_json, enrich_with_openalex, load_json, record_path_iter


def fetch_openalex_work(record: dict, api_base: str, mailto: str | None = None) -> tuple[dict | None, str]:
    headers = {"User-Agent": "paper-list/1.0"}
    params = {}
    if mailto:
        params["mailto"] = mailto

    if record.get("doi"):
        url = f"{api_base.rstrip('/')}/works/https://doi.org/{record['doi']}"
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.ok:
            return response.json(), response.url

    if record.get("paper_url") and "arxiv.org/abs/" in record["paper_url"]:
        arxiv_id = record["paper_url"].rstrip("/").split("/")[-1]
        url = f"{api_base.rstrip('/')}/works"
        params["filter"] = f"locations.landing_page_url:https://arxiv.org/abs/{arxiv_id}"
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if results:
            return results[0], response.url

    title = record.get("title", "")
    url = f"{api_base.rstrip('/')}/works"
    params["search"] = title
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []
    return (results[0], response.url) if results else (None, response.url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich normalized PapersWithCode records with OpenAlex metadata.")
    parser.add_argument(
        "--input",
        default="data/pwc_archive/normalized/papers",
        help="Input JSON file or directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional separate output directory. Defaults to updating files in place.",
    )
    parser.add_argument("--api-base", default="https://api.openalex.org", help="OpenAlex API base URL.")
    parser.add_argument("--mailto", default=None, help="Optional contact email for polite pool requests.")
    args = parser.parse_args()

    for file_path in record_path_iter(args.input):
        record = load_json(file_path, {})
        if not record:
            continue
        try:
            work, request_url = fetch_openalex_work(record, args.api_base, args.mailto)
        except requests.RequestException as exc:
            print(f"OpenAlex request failed for {file_path.name}: {exc}")
            continue
        if not work:
            print(f"No OpenAlex match for {file_path.name}")
            continue
        enriched = enrich_with_openalex(record, work, request_url)
        target = Path(args.output_dir) / file_path.name if args.output_dir else file_path
        dump_json(target, enriched)
        print(f"OpenAlex enriched {target}")


if __name__ == "__main__":
    main()
