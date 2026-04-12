import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pwc_archive import dump_json, enrich_with_openalex, load_json, record_path_iter
from utils.state_manager import (
    cache_openalex_by_doi, get_cached_openalex_by_doi,
    cache_openalex_by_arxiv, get_cached_openalex_by_arxiv,
    cache_openalex_by_title, get_cached_openalex_by_title,
    get_cache_stats,
)

# Default TTL for OpenAlex cache: 30 days
_DEFAULT_TTL_DAYS = 30


def _build_params(mailto: str | None) -> dict:
    params = {}
    if mailto:
        params["mailto"] = mailto
    return params


def _fetch_by_doi(doi: str, api_base: str, mailto: str | None, ttl_days: int) -> tuple[dict | None, str | None]:
    """Try to fetch from cache first, then from API."""
    cached = get_cached_openalex_by_doi(doi)
    if cached:
        return cached, None  # (result, None) = cache hit
    headers = {"User-Agent": "paper-list/1.0"}
    params = _build_params(mailto)
    url = f"{api_base.rstrip('/')}/works/https://doi.org/{doi}"
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
    except requests.RequestException:
        return None, url  # (None, url) = network error, still try next strategy
    if response.ok:
        data = response.json()
        cache_openalex_by_doi(doi, json.dumps(data), response.url, ttl_days)
        return data, response.url
    return None, url


def _fetch_by_arxiv(paper_url: str, api_base: str, mailto: str | None, ttl_days: int) -> tuple[dict | None, str | None]:
    """Try to fetch from cache first, then from API."""
    if "arxiv.org/abs/" not in paper_url:
        return None, None
    arxiv_id = paper_url.rstrip("/").split("/")[-1]
    cached = get_cached_openalex_by_arxiv(arxiv_id)
    if cached:
        return cached, None
    headers = {"User-Agent": "paper-list/1.0"}
    params = _build_params(mailto)
    params["filter"] = f"locations.landing_page_url:https://arxiv.org/abs/{arxiv_id}"
    url = f"{api_base.rstrip('/')}/works"
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
    except requests.RequestException:
        return None, url
    if response.ok:
        payload = response.json()
        results = payload.get("results") or []
        if results:
            data = results[0]
            cache_openalex_by_arxiv(arxiv_id, json.dumps(data), response.url, ttl_days)
            return data, response.url
    return None, url


def _fetch_by_title(title: str, api_base: str, mailto: str | None, ttl_days: int) -> tuple[dict | None, str | None]:
    """Fetch by title search, try cache first."""
    if not title:
        return None, None
    cached = get_cached_openalex_by_title(title)
    if cached:
        return cached, None
    headers = {"User-Agent": "paper-list/1.0"}
    params = _build_params(mailto)
    params["search"] = title
    url = f"{api_base.rstrip('/')}/works"
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
    except requests.RequestException:
        return None, url
    if response.ok:
        payload = response.json()
        results = payload.get("results") or []
        if results:
            data = results[0]
            cache_openalex_by_title(title, json.dumps(data), response.url, ttl_days)
            return data, response.url
    return None, url


def fetch_openalex_work(
    record: dict,
    api_base: str,
    mailto: str | None = None,
    ttl_days: int = _DEFAULT_TTL_DAYS,
) -> tuple[dict | None, str]:
    """
    Fetch OpenAlex metadata for a record using a three-tier lookup strategy:
    1. DOI (most reliable, always tried first)
    2. arXiv ID (fallback)
    3. Title search (last resort)

    Each tier checks the SQLite cache before hitting the API.
    Returns (work_data, last_request_url). work_data is None on total failure.
    """
    # Tier 1: DOI
    if record.get("doi"):
        work, _ = _fetch_by_doi(record["doi"], api_base, mailto, ttl_days)
        if work:
            return work, f"{api_base}/works/https://doi.org/{record['doi']}"

    # Tier 2: arXiv
    if record.get("paper_url"):
        work, _ = _fetch_by_arxiv(record["paper_url"], api_base, mailto, ttl_days)
        if work:
            return work, f"{api_base}/works (arXiv lookup)"

    # Tier 3: Title
    title = record.get("title", "")
    if title:
        work, request_url = _fetch_by_title(title, api_base, mailto, ttl_days)
        if work:
            return work, request_url or f"{api_base}/works (title search)"

    return None, f"{api_base}/works (no match)"


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
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=_DEFAULT_TTL_DAYS,
        help=f"Cache TTL in days (default: {_DEFAULT_TTL_DAYS}).",
    )
    parser.add_argument(
        "--show-cache-stats",
        action="store_true",
        help="Print cache statistics at the end.",
    )
    args = parser.parse_args()

    for file_path in record_path_iter(args.input):
        record = load_json(file_path, {})
        if not record:
            continue
        try:
            work, request_url = fetch_openalex_work(record, args.api_base, args.mailto, args.ttl_days)
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

    if args.show_cache_stats:
        stats = get_cache_stats()
        print(
            f"Cache stats — total: {stats['total']}, "
            f"expired: {stats['expired']}, total_hits: {stats['total_hits']}"
        )


if __name__ == "__main__":
    main()
