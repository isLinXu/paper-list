"""Concurrent paper fetching with deduplication and incremental support.

Wraps get_daily_papers to fetch multiple topics concurrently,
deduplicate cross-topic papers, and respect API rate limits.

Incremental mode:
  When incremental=True, the fetcher checks the topic_fetch_log in SQLite
  to determine the last successful fetch time for each topic. If a topic
  was recently fetched (within the lookback window), it is skipped unless
  forced. This avoids redundant API calls for topics that haven't changed.

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

import hashlib
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
                     incremental: bool = False,
                     incremental_lookback_hours: int = 20,
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
        incremental: If True, skip topics that were successfully fetched
                     within the lookback window (saves API quota)
        incremental_lookback_hours: Skip topics fetched within this many hours

    Returns:
        (data_list, data_web_list, dup_map)
    """
    # --- Incremental mode: check which topics need fetching ---
    skipped_topics = set()
    if incremental:
        try:
            from . import state_manager as _sm
            last_fetches = _sm.get_all_topic_last_fetches()
            now = time.time()
            lookback_secs = incremental_lookback_hours * 3600

            for topic in list(keywords.keys()):
                info = last_fetches.get(topic)
                if info and (now - info["last_fetch"]) < lookback_secs:
                    skipped_topics.add(topic)
                    hours_ago = (now - info["last_fetch"]) / 3600
                    logging.info(
                        f"[incremental] Skipping '{topic}' — "
                        f"fetched {hours_ago:.1f}h ago "
                        f"(lookback={incremental_lookback_hours}h)"
                    )

            if skipped_topics:
                logging.info(
                    f"[incremental] Skipping {len(skipped_topics)}/{len(keywords)} topics "
                    f"(recently fetched)"
                )
        except Exception as e:
            logging.warning(f"[incremental] State check failed, falling back to full fetch: {e}")

    # Filter out skipped topics
    active_keywords = {
        k: v for k, v in keywords.items() if k not in skipped_topics
    }

    if not active_keywords:
        logging.info("[incremental] All topics recently fetched — nothing to do")
        return [], [], {}

    # Expand multi-bucket topics into individual fetch tasks
    fetch_tasks: list[tuple[str, str, int]] = []  # (topic, query, bucket_index)
    topic_bucket_map: dict[str, list[int]] = {}  # topic -> [task indices]

    for topic, query in active_keywords.items():
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
        f"Fetching {len(active_keywords)} topics ({len(fetch_tasks)} API calls, "
        f"workers={max_workers})"
    )
    if skipped_topics:
        logging.info(f"  Skipped {len(skipped_topics)} recently-fetched topics")

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

                # Log to state_manager for incremental tracking
                try:
                    from . import state_manager as _sm
                    qhash = hashlib.md5(query.encode()).hexdigest()[:8]
                    _sm.log_topic_fetch(
                        topic=topic,
                        bucket_index=max(bucket_idx, 0),
                        query_hash=qhash,
                        fetch_status="success",
                        papers_found=paper_count,
                    )
                except Exception:
                    pass  # Non-fatal

            except Exception as e:
                logging.error(f"Failed to fetch '{label}': {e}")
                raw_results[task_idx] = ({topic: {}}, {topic: {}})

                # Log failure
                try:
                    from . import state_manager as _sm
                    qhash = hashlib.md5(query.encode()).hexdigest()[:8]
                    _sm.log_topic_fetch(
                        topic=topic,
                        bucket_index=max(bucket_idx, 0),
                        query_hash=qhash,
                        fetch_status="error",
                        error_msg=str(e)[:200],
                    )
                except Exception:
                    pass

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
