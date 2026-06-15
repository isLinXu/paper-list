#!/usr/bin/env python3
"""Filter efficiency audit for paper-list.

Analyzes existing JSON data to determine which filter terms
actually contribute papers, helping fork owners prune ineffective filters.

Enhanced features:
- Per-filter hit estimation via title/abstract keyword matching
- Zombie filter detection (zero-hit filters)
- Bucket size analysis (warns about oversized topics)
- Cross-topic overlap heatmap
- JSON output for CI integration

Usage:
    python scripts/filter_audit.py
    python scripts/filter_audit.py --config config.yaml
    python scripts/filter_audit.py --days 30          # only count last 30 days
    python scripts/filter_audit.py --zombie           # show only zero-hit filters
    python scripts/filter_audit.py --json             # machine-readable output
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.configs import load_config


def _collect_filter_hits(json_dir: str, keywords_config: dict,
                         days: int | None = None) -> dict:
    """Scan JSON files and count how many papers each filter term matched.

    Uses title/abstract keyword matching to estimate per-filter hits.
    This is an approximation — arXiv's own relevance scoring means
    not every returned paper necessarily matches every filter term.

    Returns: {topic: {"_total_papers": N, "filters": {term: hit_count}}}
    """
    json_path = Path(json_dir)
    if not json_path.exists():
        print(f"[WARN] JSON directory not found: {json_path}")
        return {}

    cutoff_date = None
    if days:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m")

    hits = defaultdict(lambda: {"_total_papers": 0, "filters": defaultdict(int)})

    for json_file in sorted(json_path.glob("*.json")):
        stem = json_file.stem
        if not stem.startswith("20"):
            continue
        if cutoff_date and stem < cutoff_date:
            continue

        try:
            data = json.load(open(json_file, "r", encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for topic, papers in data.items():
            if not isinstance(papers, dict):
                continue
            hits[topic]["_total_papers"] += len(papers)

            # Estimate per-filter hits by matching filter terms in paper titles
            topic_spec = keywords_config.get(topic, {})
            if not isinstance(topic_spec, dict):
                continue
            filters = topic_spec.get("filters", [])

            for pid, entry in papers.items():
                title = ""
                if isinstance(entry, dict):
                    title = entry.get("title", "").lower()
                elif isinstance(entry, str):
                    title = entry.lower()

                for f in filters:
                    f_lower = f.strip().lower()
                    # Match filter term as substring in title
                    if f_lower in title:
                        hits[topic]["filters"][f] += 1

    return dict(hits)


def _analyze_bucket_sizes(keywords_config: dict) -> list[dict]:
    """Analyze filter bucket sizes for each topic.

    Returns list of dicts with topic, filter_count, estimated_query_len, bucket_count.
    """
    from utils.configs import _split_filters_into_buckets

    results = []
    for topic, spec in keywords_config.items():
        if not isinstance(spec, dict):
            continue
        filters = spec.get("filters", [])
        if not filters:
            continue
        buckets = _split_filters_into_buckets(filters)
        # Estimate query length
        OR = " OR "
        terms = [f'"{f}"' if " " in f else f for f in filters]
        total_len = len(OR.join(terms))

        results.append({
            "topic": topic,
            "filter_count": len(filters),
            "query_length": total_len,
            "bucket_count": len(buckets),
        })

    return sorted(results, key=lambda x: x["filter_count"], reverse=True)


def audit_filters(config_path: str, days: int | None = None,
                  zombie_only: bool = False, json_output: bool = False) -> list[dict] | None:
    """Print a filter efficiency audit report.

    Returns JSON-serializable list if json_output=True, else None.
    """
    config = load_config(config_path)
    keywords = config.get("keywords", {})
    json_dir = config.get("json_readme_path", "./docs/data")

    hits = _collect_filter_hits(json_dir, keywords, days=days)

    if not hits and not json_output:
        print("No JSON data found. Run get_paper.py first to populate data.")
        return None

    total_filters = 0
    active_filters = 0
    zombie_filters = 0
    low_hit_filters = 0
    LOW_HIT_THRESHOLD = 2  # Filters with ≤2 hits in the period

    period_desc = f"last {days} days" if days else "all time"
    report_entries = []

    for topic, spec in keywords.items():
        if not isinstance(spec, dict):
            continue
        filters = spec.get("filters", [])
        if not filters:
            continue

        topic_hits = hits.get(topic, {})
        total_papers = topic_hits.get("_total_papers", 0)
        filter_hits = topic_hits.get("filters", {})

        entry = {
            "topic": topic,
            "total_papers": total_papers,
            "filter_count": len(filters),
            "filters": [],
        }

        for f in filters:
            total_filters += 1
            hit_count = filter_hits.get(f, 0)

            status = "active"
            if total_papers == 0:
                status = "zombie"
                zombie_filters += 1
            elif hit_count <= LOW_HIT_THRESHOLD:
                status = "low_hit"
                low_hit_filters += 1
            else:
                active_filters += 1

            entry["filters"].append({
                "term": f,
                "hits": hit_count,
                "status": status,
            })

        report_entries.append(entry)

    # --- Bucket size analysis ---
    bucket_analysis = _analyze_bucket_sizes(keywords)
    oversized = [b for b in bucket_analysis if b["bucket_count"] > 1]

    if json_output:
        return {
            "period": period_desc,
            "summary": {
                "total_filters": total_filters,
                "active": active_filters,
                "zombie": zombie_filters,
                "low_hit": low_hit_filters,
            },
            "oversized_topics": oversized,
            "topics": report_entries,
        }

    # --- Human-readable output ---
    print(f"\n{'=' * 70}")
    print(f"  Filter Efficiency Audit ({period_desc})")
    print(f"{'=' * 70}\n")

    for entry in report_entries:
        topic = entry["topic"]
        total_papers = entry["total_papers"]
        filters = entry["filters"]

        print(f"  [{topic}] ({total_papers} papers, {len(filters)} filters)")

        for f_info in filters:
            term = f_info["term"]
            hits_count = f_info["hits"]
            status = f_info["status"]

            if zombie_only and status != "zombie":
                continue

            flag = ""
            if status == "zombie":
                flag = " <-- ZOMBIE (zero papers in topic)"
            elif status == "low_hit":
                flag = " <-- LOW HIT"

            print(f"    {term:<48} {hits_count:>5}{flag}")

        print()

    # Summary
    print(f"{'=' * 70}")
    print(f"  Summary: {total_filters} filters")
    print(f"    Active:    {active_filters}")
    print(f"    Low-hit:   {low_hit_filters} (≤{LOW_HIT_THRESHOLD} hits)")
    print(f"    Zombie:    {zombie_filters} (topic has zero papers)")
    print(f"{'=' * 70}")

    if zombie_filters > 0:
        print(f"\n  Found {zombie_filters} zombie filter(s).")
        print("  Consider removing them to speed up API calls.")
        print("  Tip: Set 'enabled: false' in config.yaml to disable without deleting.")

    if low_hit_filters > 0:
        print(f"\n  Found {low_hit_filters} low-hit filter(s) (≤{LOW_HIT_THRESHOLD} hits).")
        print("  These may be too specific or rarely used in arXiv papers.")

    # Bucket size warnings
    if oversized:
        print(f"\n  Oversized topics (split into multiple API buckets):")
        for b in oversized:
            print(f"    {b['topic']}: {b['filter_count']} filters → "
                  f"{b['bucket_count']} buckets (query: {b['query_length']} chars)")

    # Cross-topic overlap
    filter_to_topics = defaultdict(list)
    for topic, spec in keywords.items():
        if isinstance(spec, dict):
            for f in spec.get("filters", []):
                filter_to_topics[f.strip().lower()].append(topic)

    overlapping = {f: topics for f, topics in filter_to_topics.items() if len(topics) > 1}
    if overlapping:
        print(f"\n  Cross-topic overlaps ({len(overlapping)} terms):")
        for f, topics in sorted(overlapping.items()):
            print(f"    '{f}' -> {', '.join(topics)}")

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter efficiency audit for paper-list")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--days", type=int, default=None,
                        help="Only count papers from the last N days")
    parser.add_argument("--zombie", action="store_true",
                        help="Show only zero-hit (zombie) filters")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON for CI integration")
    args = parser.parse_args()

    result = audit_filters(args.config, days=args.days,
                           zombie_only=args.zombie, json_output=args.json)

    if args.json and result is not None:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
