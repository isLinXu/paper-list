"""Concurrent paper fetching with deduplication.

Wraps get_daily_papers to fetch multiple topics concurrently,
deduplicate cross-topic papers, and respect API rate limits.

Usage (drop-in replacement in get_paper.py):
    from utils.concurrent_fetch import fetch_all_topics

    results = fetch_all_topics(
        keywords=config['kv'],
        keywords_config=config['keywords'],
        max_results=config['max_results'],
        start_date=config['start_date'],
        end_date=config['end_date'],
    )
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .get_infos import get_daily_papers


# Rate-limit lock: ensure we don't overwhelm the arXiv API.
# arXiv recommends at least 3 seconds between requests.
_api_lock = threading.Lock()
_last_request_time = 0.0
_MIN_INTERVAL = 3.0  # seconds between API calls


def _rate_limited_fetch(topic: str, query: str, max_results: int,
                        start_date: str | None, end_date: str | None
                        ) -> tuple[dict, dict]:
    """Fetch a single topic with rate limiting."""
    global _last_request_time

    with _api_lock:
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_INTERVAL:
            wait = _MIN_INTERVAL - elapsed
            logging.debug(f"Rate-limit: waiting {wait:.1f}s before fetching '{topic}'")
            time.sleep(wait)
        _last_request_time = time.time()

    return get_daily_papers(topic, query=query, max_results=max_results,
                           start_date=start_date, end_date=end_date)


def _deduplicate_cross_topic(results: list[tuple[dict, dict]]
                              ) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
    """Deduplicate papers that appear in multiple topics.

    Returns:
        (deduplicated_data, deduplicated_data_web, dup_map)
        dup_map: {paper_id: [topic1, topic2, ...]} for cross-reference
    """
    seen_ids: dict[str, str] = {}  # paper_id -> first_topic
    dup_map: dict[str, list[str]] = {}
    deduped = []
    deduped_web = []

    for data, data_web in results:
        deduped_chunk = {}
        deduped_web_chunk = {}

        for topic, papers in data.items():
            filtered = {}
            for pid, entry in papers.items():
                if pid in seen_ids:
                    # Duplicate: record cross-reference but skip
                    dup_map.setdefault(pid, [seen_ids[pid]]).append(topic)
                    logging.debug(f"Dedup: {pid} already in '{seen_ids[pid]}', skipping in '{topic}'")
                else:
                    seen_ids[pid] = topic
                    filtered[pid] = entry

            deduped_chunk[topic] = filtered

        for topic, papers in data_web.items():
            deduped_web_chunk[topic] = {
                pid: entry for pid, entry in papers.items()
                if pid in deduped_chunk.get(topic, {})
            }

        deduped.append(deduped_chunk)
        deduped_web.append(deduped_web_chunk)

    if dup_map:
        logging.info(f"Deduplicated {len(dup_map)} cross-topic papers")

    return deduped, deduped_web, dup_map


def fetch_all_topics(keywords: dict[str, str],
                     keywords_config: dict | None = None,
                     max_results: int = 100,
                     start_date: str | None = None,
                     end_date: str | None = None,
                     max_workers: int = 3,
                     deduplicate: bool = True,
                     ) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
    """Fetch all topics concurrently with rate limiting and deduplication.

    Args:
        keywords: {topic: query_string} from config['kv']
        keywords_config: Full keywords config (for future use)
        max_results: Max papers per topic
        start_date: Optional start date filter
        end_date: Optional end date filter
        max_workers: Max concurrent threads (default 3, safe for arXiv API)
        deduplicate: Whether to deduplicate cross-topic papers

    Returns:
        (data_list, data_web_list, dup_map)
    """
    topics = list(keywords.keys())
    logging.info(f"Fetching {len(topics)} topics concurrently (workers={max_workers})")

    results = []
    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for topic, query in keywords.items():
            future = executor.submit(
                _rate_limited_fetch,
                topic, query, max_results, start_date, end_date,
            )
            futures[future] = topic

        for future in as_completed(futures):
            topic = futures[future]
            try:
                result = future.result()
                results.append(result)
                paper_count = len(result[0].get(topic, {}))
                logging.info(f"Fetched '{topic}': {paper_count} papers")
            except Exception as e:
                logging.error(f"Failed to fetch '{topic}': {e}")
                # Insert empty result so downstream logic doesn't break
                results.append(({topic: {}}, {topic: {}}))

    if deduplicate:
        deduped, deduped_web, dup_map = _deduplicate_cross_topic(results)
        return deduped, deduped_web, dup_map

    # No deduplication
    data_list = [r[0] for r in results]
    data_web_list = [r[1] for r in results]
    return data_list, data_web_list, {}
