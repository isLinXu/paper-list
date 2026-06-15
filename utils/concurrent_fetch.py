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


def _merge_bucket_results(
    topic: str,
    bucket_results: list[tuple[dict, dict]],
) -> tuple[dict, dict]:
    """Merge results from multiple query buckets for the same topic.

    Deduplicates by paper_id within the topic (first occurrence wins).
    """
    merged_data: dict[str, dict] = {}
    merged_web: dict[str, dict] = {}

    for data, data_web in bucket_results:
        for t, papers in data.items():
            if t not in merged_data:
                merged_data[t] = {}
            for pid, entry in papers.items():
                if pid not in merged_data[t]:
                    merged_data[t][pid] = entry

        for t, papers in data_web.items():
            if t not in merged_web:
                merged_web[t] = {}
            for pid, entry in papers.items():
                if pid not in merged_web[t]:
                    merged_web[t][pid] = entry

    return merged_data, merged_web


def fetch_all_topics(keywords: dict[str, str | list[str]],
                     keywords_config: dict | None = None,
                     max_results: int = 100,
                     start_date: str | None = None,
                     end_date: str | None = None,
                     max_workers: int = 3,
                     deduplicate: bool = True,
                     ) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
    """Fetch all topics concurrently with rate limiting and deduplication.

    Args:
        keywords: {topic: query_string} or {topic: [bucket1, bucket2, ...]}
                  from config['kv']. Multi-bucket topics are split into
                  separate API calls and merged.
        keywords_config: Full keywords config (for future use)
        max_results: Max papers per topic
        start_date: Optional start date filter
        end_date: Optional end date filter
        max_workers: Max concurrent threads (default 3, safe for arXiv API)
        deduplicate: Whether to deduplicate cross-topic papers

    Returns:
        (data_list, data_web_list, dup_map)
    """
    # Expand multi-bucket topics into individual fetch tasks
    fetch_tasks: list[tuple[str, str, int]] = []  # (topic, query, bucket_index)
    topic_bucket_map: dict[str, list[int]] = {}  # topic -> [task indices]

    for topic, query in keywords.items():
        if isinstance(query, list):
            # Multi-bucket topic: each bucket is a separate query
            for i, bucket_query in enumerate(query):
                idx = len(fetch_tasks)
                fetch_tasks.append((topic, bucket_query, i))
                topic_bucket_map.setdefault(topic, []).append(idx)
        else:
            idx = len(fetch_tasks)
            fetch_tasks.append((topic, query, -1))
            topic_bucket_map.setdefault(topic, []).append(idx)

    logging.info(
        f"Fetching {len(keywords)} topics ({len(fetch_tasks)} API calls, "
        f"workers={max_workers})"
    )

    raw_results: dict[int, tuple[dict, dict]] = {}
    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for task_idx, (topic, query, bucket_idx) in enumerate(fetch_tasks):
            # For multi-bucket topics, use a sub-label for logging
            label = f"{topic}[bucket{bucket_idx}]" if bucket_idx >= 0 else topic
            future = executor.submit(
                _rate_limited_fetch,
                label, query, max_results, start_date, end_date,
            )
            futures[future] = task_idx

        for future in as_completed(futures):
            task_idx = futures[future]
            topic, query, bucket_idx = fetch_tasks[task_idx]
            label = f"{topic}[bucket{bucket_idx}]" if bucket_idx >= 0 else topic
            try:
                result = future.result()
                raw_results[task_idx] = result
                paper_count = len(result[0].get(label, result[0].get(topic, {})))
                logging.info(f"Fetched '{label}': {paper_count} papers")
            except Exception as e:
                logging.error(f"Failed to fetch '{label}': {e}")
                raw_results[task_idx] = ({topic: {}}, {topic: {}})

    # Merge multi-bucket results per topic, then assemble final list
    results = []
    for topic in keywords.keys():
        bucket_indices = topic_bucket_map[topic]
        if len(bucket_indices) == 1:
            # Single bucket (or single query) — use directly
            task_idx = bucket_indices[0]
            _, _, bucket_idx = fetch_tasks[task_idx]
            label = f"{topic}[bucket{bucket_idx}]" if bucket_idx >= 0 else topic
            data, data_web = raw_results.get(task_idx, ({topic: {}}, {topic: {}}))
            # Normalize key to topic name (bucket labels use topic[bucketN])
            if label in data and label != topic:
                data = {topic: data[label]}
                data_web = {topic: data_web.get(label, {})}
            results.append((data, data_web))
        else:
            # Multi-bucket: merge all buckets for this topic
            bucket_results = []
            for task_idx in bucket_indices:
                _, _, bucket_idx = fetch_tasks[task_idx]
                label = f"{topic}[bucket{bucket_idx}]"
                data, data_web = raw_results.get(task_idx, ({topic: {}}, {topic: {}}))
                # Normalize key
                if label in data:
                    data = {topic: data[label]}
                    data_web = {topic: data_web.get(label, {})}
                bucket_results.append((data, data_web))
            merged_data, merged_web = _merge_bucket_results(topic, bucket_results)
            total = len(merged_data.get(topic, {}))
            logging.info(f"Merged {len(bucket_results)} buckets for '{topic}': {total} papers")
            results.append((merged_data, merged_web))

    if deduplicate:
        deduped, deduped_web, dup_map = _deduplicate_cross_topic(results)
        return deduped, deduped_web, dup_map

    # No deduplication
    data_list = [r[0] for r in results]
    data_web_list = [r[1] for r in results]
    return data_list, data_web_list, {}
