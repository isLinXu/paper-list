"""Semantic Scholar integration for paper enrichment.

Replaces the disabled HuggingFace papers page with Semantic Scholar API,
which is more stable and provides richer metadata (citation counts,
influential citations, tldr summaries).

API docs: https://api.semanticscholar.org/api-docs/
Rate limits: 100 requests/5 min (unauthenticated), 1 req/sec recommended.
"""
from __future__ import annotations

import logging
import os
import time
import requests
from functools import lru_cache

# Semantic Scholar API base
S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Fields we want from the paper endpoint
PAPER_FIELDS = "title,citationCount,influentialCitationCount,tldr,openAccessPdf"

# Simple in-memory rate limiter
_last_s2_request = 0.0
_S2_MIN_INTERVAL = 1.1  # seconds (stay under 1 req/sec)


def _rate_limit() -> None:
    """Simple rate limiter for Semantic Scholar API."""
    global _last_s2_request
    elapsed = time.time() - _last_s2_request
    if elapsed < _S2_MIN_INTERVAL:
        time.sleep(_S2_MIN_INTERVAL - elapsed)
    _last_s2_request = time.time()


def fetch_paper_metadata(arxiv_id: str) -> dict | None:
    """Fetch enriched metadata from Semantic Scholar for an arXiv paper.

    Args:
        arxiv_id: arXiv ID (e.g., "2401.12345")

    Returns:
        Dict with keys: citation_count, influential_citation_count, tldr, open_access_pdf
        None if the paper is not found or the API fails.
    """
    _rate_limit()

    url = f"{S2_BASE_URL}/paper/ArXiv:{arxiv_id}"
    params = {"fields": PAPER_FIELDS}

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            logging.warning("Semantic Scholar rate limited, backing off...")
            time.sleep(5)
            return None
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logging.debug(f"S2 API error for {arxiv_id}: {e}")
        return None

    result = {
        "citation_count": data.get("citationCount", 0),
        "influential_citation_count": data.get("influentialCitationCount", 0),
    }

    # TLDR summary (if available)
    tldr = data.get("tldr")
    if tldr and isinstance(tldr, dict):
        result["tldr"] = tldr.get("text", "")

    # Open access PDF
    oapdf = data.get("openAccessPdf")
    if oapdf and isinstance(oapdf, dict):
        result["open_access_pdf"] = oapdf.get("url", "")

    return result


def try_semantic_scholar_repo(arxiv_id: str) -> str | None:
    """Try to find a GitHub repo linked from Semantic Scholar.

    Uses the paper's externalIds and references to find associated code.
    Falls back gracefully if not found.
    """
    _rate_limit()

    url = f"{S2_BASE_URL}/paper/ArXiv:{arxiv_id}"
    params = {"fields": "externalIds,url"}

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except requests.RequestException:
        return None

    # Semantic Scholar doesn't directly provide code links,
    # but we can check if there's a GitHub URL in the paper metadata
    # For now, return None and let GitHub API search handle it
    return None


def enrich_paper_record(record: dict) -> dict:
    """Enrich a paper record with Semantic Scholar metadata.

    Adds citation counts and TLDR summary if available.
    Does NOT overwrite existing fields.
    """
    arxiv_id = record.get("arxiv_id", "")
    if not arxiv_id:
        return record

    metadata = fetch_paper_metadata(arxiv_id)
    if metadata is None:
        return record

    # Only add fields that aren't already present
    if "citation_count" not in record and "citation_count" in metadata:
        record["citation_count"] = metadata["citation_count"]
    if "influential_citation_count" not in record and "influential_citation_count" in metadata:
        record["influential_citation_count"] = metadata["influential_citation_count"]
    if "tldr" not in record and "tldr" in metadata:
        record["tldr"] = metadata["tldr"]

    return record
