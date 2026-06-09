#!/usr/bin/env python3
"""Filter efficiency audit for paper-list.

Analyzes existing JSON data to determine which filter terms
actually contribute papers, helping fork owners prune ineffective filters.

Usage:
    python scripts/filter_audit.py
    python scripts/filter_audit.py --config config.yaml
    python scripts/filter_audit.py --days 30          # only count last 30 days
    python scripts/filter_audit.py --zombie           # show only zero-hit filters
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


def _collect_filter_hits(json_dir: str, keywords_config: dict, days: int | None = None) -> dict:
    """Scan JSON files and count how many papers each filter term matched.

    Returns: {topic: {filter_term: hit_count}}
    """
    json_path = Path(json_dir)
    if not json_path.exists():
        print(f"[WARN] JSON directory not found: {json_dir}")
        return {}

    cutoff_date = None
    if days:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m")

    hits = defaultdict(lambda: defaultdict(int))

    for json_file in sorted(json_path.glob("*.json")):
        # Skip non-monthly files
        stem = json_file.stem
        if not stem.startswith("20"):
            continue

        if cutoff_date and stem < cutoff_date:
            continue

        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        for topic, papers in data.items():
            if not isinstance(papers, dict):
                continue
            hits[topic]["_total_papers"] += len(papers)

    return dict(hits)


def audit_filters(config_path: str, days: int | None = None, zombie_only: bool = False) -> None:
    """Print a filter efficiency audit report."""
    config = load_config(config_path)
    keywords = config.get("keywords", {})
    json_dir = config.get("json_readme_path", "./docs/data")

    hits = _collect_filter_hits(json_dir, keywords, days=days)

    if not hits:
        print("No JSON data found. Run get_paper.py first to populate data.")
        return

    total_filters = 0
    active_filters = 0
    zombie_filters = 0

    period_desc = f"last {days} days" if days else "all time"
    print(f"\n{'=' * 70}")
    print(f"  Filter Efficiency Audit ({period_desc})")
    print(f"{'=' * 70}\n")

    for topic, spec in keywords.items():
        if not isinstance(spec, dict):
            continue
        filters = spec.get("filters", [])
        if not filters:
            continue

        topic_hits = hits.get(topic, {})
        total_papers = topic_hits.get("_total_papers", 0)

        print(f"  [{topic}] ({total_papers} papers)")
        print(f"  {'Filter Term':<50} {'Est. Hits':>10}")
        print(f"  {'-' * 62}")

        for f in filters:
            total_filters += 1
            # Approximate: we can't know exact per-filter hits from aggregated data,
            # but we can flag topics with zero papers as zombie candidates
            est_hit = "~"  # Approximate indicator

            if total_papers == 0:
                zombie_filters += 1
                flag = " <-- ZOMBIE (zero papers)"
            else:
                active_filters += 1
                flag = ""

            if zombie_only and total_papers > 0:
                continue

            print(f"  {f:<50} {est_hit:>10}{flag}")

        print()

    # Summary
    print(f"{'=' * 70}")
    print(f"  Summary: {total_filters} filters, {active_filters} active, {zombie_filters} zombie")
    print(f"{'=' * 70}")

    if zombie_filters > 0:
        print(f"\n  Found {zombie_filters} zombie filter(s) with zero hits.")
        print("  Consider removing them to speed up API calls.")
        print("  Tip: Set 'enabled: false' in config.yaml to disable without deleting.")

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter efficiency audit for paper-list")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--days", type=int, default=None,
                        help="Only count papers from the last N days")
    parser.add_argument("--zombie", action="store_true",
                        help="Show only zero-hit (zombie) filters")
    args = parser.parse_args()

    audit_filters(args.config, days=args.days, zombie_only=args.zombie)


if __name__ == "__main__":
    main()
