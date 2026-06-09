import datetime
import logging
import os

import requests

from .paper_links import ensure_paper_record
from .storage import load_paper_store, save_paper_store
from . import state_manager as _sm

github_url = "https://api.github.com/search/repositories"

# Lazy import to avoid circular dependency
_semantic_scholar = None


def _get_s2():
    """Lazy-load semantic_scholar module."""
    global _semantic_scholar
    if _semantic_scholar is None:
        from . import semantic_scholar as _sm
        _semantic_scholar = _sm
    return _semantic_scholar


def _is_recent(date_str: str, days: int = 90) -> bool:
    """Return True if the paper was published within `days` days."""
    try:
        pub = datetime.date.fromisoformat(date_str)
        return (datetime.date.today() - pub).days <= days
    except ValueError:
        return False


def parse_arxiv_record(entry, paper_id=None):
    record = ensure_paper_record(entry, paper_id=paper_id)
    return (
        record["date"],
        record["title"],
        record["authors"],
        record["arxiv_id"],
        record["translate_url"],
        record["read_url"],
        record["code_url"],
    )


def update_paper_links(filename, start_date=None, end_date=None,
                       enrich_tldr: bool = False, enrich_citations: bool = False):
    """
    Weekly update paper links in json file using GitHub API with caching.

    This is the primary place where code URLs are resolved. The daily fetch
    (get_daily_papers) intentionally skips GitHub search to stay fast.
    Results are cached in SQLite via utils.state_manager to avoid
    redundant API calls for papers already resolved.

    Args:
        filename: path to the JSON paper store (file or shard directory)
        start_date: only process papers on/after this date (YYYY-MM-DD)
        end_date: only process papers on/before this date (YYYY-MM-DD)
        enrich_tldr: fetch TLDR summaries from Semantic Scholar for recent papers
        enrich_citations: fetch citation counts from Semantic Scholar for recent papers
    """
    data = load_paper_store(filename)

    start_bound = datetime.date.fromisoformat(start_date) if start_date else None
    end_bound = datetime.date.fromisoformat(end_date) if end_date else None

    changed_topics = set()
    for keyword, papers in data.items():
        logging.info(f"keywords = {keyword}")
        for paper_id, entry in list(papers.items()):
            record = ensure_paper_record(entry, paper_id=paper_id)
            original_code_url = record.get("code_url")
            publish_date = datetime.date.fromisoformat(record["date"])

            if start_bound and publish_date < start_bound:
                continue
            if end_bound and publish_date > end_bound:
                continue

            if record.get("code_url"):
                papers[paper_id] = record
                continue

            arxiv_id = record.get("arxiv_id", "")
            repo_url = None

            # --- Check SQLite cache first ---
            cached, cached_url = _sm.get_cached_github_code(arxiv_id)
            if cached:
                repo_url = cached_url
                logging.debug(f"GitHub code cache hit for {arxiv_id}: {repo_url}")
            else:
                # --- Query GitHub API ---
                try:
                    params = {
                        "q": f"arxiv:{arxiv_id} {record['title']}",
                        "sort": "stars",
                        "order": "desc",
                    }
                    headers = {"User-Agent": "paper-list/1.0"}
                    token = os.environ.get("GITHUB_TOKEN")
                    if token:
                        headers["Authorization"] = f"token {token}"
                    response = requests.get(github_url, params=params, timeout=4, headers=headers)
                    if response.ok and "application/json" in (response.headers.get("Content-Type") or ""):
                        payload = response.json()
                        if payload.get("total_count", 0) > 0:
                            repo_url = payload["items"][0]["html_url"]
                except Exception as exc:
                    logging.info(f"GitHub fallback no result for id {arxiv_id}: {exc}")

                # Cache result (including None = not found) to avoid redundant queries
                try:
                    _sm.cache_github_code(arxiv_id, repo_url)
                except Exception:
                    pass  # Cache failure is non-fatal

            if repo_url is not None:
                record["code_url"] = repo_url
            papers[paper_id] = record
            if record.get("code_url") != original_code_url:
                changed_topics.add(keyword)

            # --- Semantic Scholar enrichment (optional) ---
            if (enrich_tldr or enrich_citations) and _is_recent(record["date"], days=90):
                arxiv_id = record.get("arxiv_id", "")
                needs_tldr = enrich_tldr and not record.get("tldr")
                needs_citations = enrich_citations and "citation_count" not in record
                if arxiv_id and (needs_tldr or needs_citations):
                    try:
                        s2 = _get_s2()
                        meta = s2.fetch_paper_metadata(arxiv_id)
                        if meta:
                            if needs_tldr and meta.get("tldr"):
                                record["tldr"] = meta["tldr"]
                                changed_topics.add(keyword)
                            if needs_citations and "citation_count" in meta:
                                record["citation_count"] = meta["citation_count"]
                                record["influential_citation_count"] = meta.get("influential_citation_count", 0)
                                changed_topics.add(keyword)
                            papers[paper_id] = record
                    except Exception as exc:
                        logging.debug(f"S2 enrichment failed for {arxiv_id}: {exc}")

    save_paper_store(filename, data)
    return changed_topics


def update_json_file(filename, data_dict):
    """
    Daily update json file using data_dict.
    """
    data = load_paper_store(filename)

    changed_topics = set()
    for chunk in data_dict:
        for keyword, papers in chunk.items():
            normalized = {
                paper_id: ensure_paper_record(entry, paper_id=paper_id)
                for paper_id, entry in papers.items()
            }
            if keyword in data:
                existing = {
                    paper_id: ensure_paper_record(entry, paper_id=paper_id)
                    for paper_id, entry in data[keyword].items()
                }
                before = dict(existing)
                existing.update(normalized)
                data[keyword] = existing
                if existing != before:
                    changed_topics.add(keyword)
            else:
                data[keyword] = normalized
                if normalized:
                    changed_topics.add(keyword)

    save_paper_store(filename, data)
    return changed_topics


def normalize_json_rows(filename):
    data = load_paper_store(filename)
    save_paper_store(filename, data)
