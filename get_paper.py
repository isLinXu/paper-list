
import logging
import argparse
import sys
import os

# Ensure project root is at the front of sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.configs import load_config
from utils.get_infos import get_daily_papers
from utils.json_tools import json_to_md, load_topic_groups_from_config
from utils.updates import update_paper_links, update_json_file
from utils.concurrent_fetch import fetch_all_topics

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)

base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
github_url = "https://api.github.com/search/repositories"
arxiv_url = "https://arxiv.org/"


def _update_source(json_file, data_collector, config, changed_cache):
    """Update a JSON data source, avoiding duplicate update_paper_links calls.

    Caches results by json_file path so that the same source is only
    updated once even when multiple outputs (README, GitPage, Wechat)
    share the same JSON file.
    """
    if json_file in changed_cache:
        return changed_cache[json_file]

    if config['update_paper_links']:
        changed = update_paper_links(
            json_file,
            start_date=config.get('start_date'),
            end_date=config.get('end_date'),
            enrich_tldr=config.get('enrich_tldr', False),
            enrich_citations=config.get('enrich_citations', False),
        )
    else:
        changed = update_json_file(json_file, data_collector)

    changed_cache[json_file] = changed
    return changed


def run(**config):
    data_collector = []
    data_collector_web = []

    keywords = config['kv']
    max_results = config['max_results']
    publish_readme = config['publish_readme']
    publish_gitpage = config['publish_gitpage']
    publish_wechat = config['publish_wechat']
    show_badge = config['show_badge']
    topic_groups = config.get('topic_groups')
    site = config.get('site')

    logging.info(f'Update Paper Link = {config["update_paper_links"]}')

    # --- Dry-run mode: preview only, no file writes ---
    if config.get('dry_run'):
        total_papers = 0
        for topic, keyword in keywords.items():
            if isinstance(keyword, list):
                # Multi-bucket topic
                bucket_total = 0
                for i, bucket_query in enumerate(keyword):
                    logging.info(f"[DRY-RUN] Fetching topic: {topic}[bucket{i}]")
                    data, _ = get_daily_papers(f"{topic}[bucket{i}]", query=bucket_query,
                                               max_results=max_results,
                                               start_date=config['start_date'], end_date=config['end_date'])
                    count = len(data.get(f"{topic}[bucket{i}]", data.get(topic, {})))
                    bucket_total += count
                    print(f"  [DRY-RUN] {topic}[bucket{i}]: {count} papers")
                total_papers += bucket_total
                print(f"  [DRY-RUN] {topic} total: {bucket_total} papers (from {len(keyword)} buckets)")
            else:
                logging.info(f"[DRY-RUN] Fetching topic: {topic}")
                data, _ = get_daily_papers(topic, query=keyword, max_results=max_results,
                                           start_date=config['start_date'], end_date=config['end_date'])
                count = len(data.get(topic, {}))
                total_papers += count
                print(f"  [DRY-RUN] {topic}: {count} papers")
        print(f"\n[DRY-RUN] Total: {total_papers} papers across {len(keywords)} topics")
        print("[DRY-RUN] No files were written. Remove --dry-run to actually fetch.")
        return

    if not config['update_paper_links']:
        logging.info("GET daily papers begin")

        # Use concurrent fetching with deduplication
        use_concurrent = config.get('concurrent_fetch', True)
        if use_concurrent and len(keywords) > 1:
            logging.info(f"Using concurrent fetch (workers={config.get('max_workers', 3)})")
            data_collector, data_collector_web, dup_map = fetch_all_topics(
                keywords=keywords,
                keywords_config=config.get('keywords'),
                max_results=max_results,
                start_date=config['start_date'],
                end_date=config['end_date'],
                max_workers=config.get('max_workers', 3),
                deduplicate=config.get('deduplicate', True),
            )
            if dup_map:
                logging.info(f"Cross-topic duplicates: {len(dup_map)} papers appeared in multiple topics")
        else:
            # Sequential fallback (original behavior)
            for topic, keyword in keywords.items():
                logging.info(f"Keyword: {topic}")
                data, data_web = get_daily_papers(topic, query=keyword, max_results=max_results,
                                                  start_date=config['start_date'], end_date=config['end_date'])
                data_collector.append(data)
                data_collector_web.append(data_web)
                print("\n")
        logging.info("GET daily papers end")

    # Cache changed topics per JSON file to avoid duplicate updates
    changed_cache = {}
    sort_mode = config.get('sort_mode', 'date')

    # 1. update README.md file
    if publish_readme:
        json_file = config['json_readme_path']
        md_file = config['md_readme_path']
        changed_readme_topics = _update_source(json_file, data_collector, config, changed_cache)
        json_to_md(json_file, md_file, task='Update Readme',
                   show_badge=show_badge, split_to_docs=True,
                   selected_topics=changed_readme_topics,
                   topic_groups=topic_groups, site=site,
                   sort_mode=sort_mode)

    # 2. update docs/index.md file (to gitpage)
    if publish_gitpage:
        json_file = config['json_gitpage_path']
        md_file = config['md_gitpage_path']
        changed_gitpage_topics = _update_source(json_file, data_collector, config, changed_cache)
        json_to_md(json_file, md_file, task='Update GitPage',
                   to_web=True, show_badge=show_badge,
                   use_tc=True, use_b2t=False, split_to_docs=True,
                   selected_topics=changed_gitpage_topics,
                   topic_groups=topic_groups, site=site,
                   sort_mode=sort_mode)

    # 3. Update docs/wechat.md file
    if publish_wechat:
        json_file = config['json_wechat_path']
        md_file = config['md_wechat_path']
        changed_wechat_topics = _update_source(json_file, data_collector_web, config, changed_cache)
        json_to_md(json_file, md_file, task='Update Wechat', to_web=False,
                   use_title=False, show_badge=show_badge,
                   topic_groups=topic_groups, site=site,
                   sort_mode=sort_mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default='config.yaml',
                        help='configuration file path')
    parser.add_argument('--update_paper_links', default=False,
                        action="store_true", help='whether to update paper links etc.')
    parser.add_argument('--start_date', type=str, default=None,
                        help='start date for fetching papers (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default=None,
                        help='end date for fetching papers (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be fetched without writing files')
    parser.add_argument('--topic', type=str, default=None,
                        help='Only fetch a single topic (exact name match)')
    args = parser.parse_args()
    config = load_config(args.config_path)
    config = {**config, "update_paper_links": args.update_paper_links}
    if args.start_date:
        config["start_date"] = args.start_date
    if args.end_date:
        config["end_date"] = args.end_date
    config["dry_run"] = args.dry_run

    # Filter to a single topic if requested
    if args.topic:
        if args.topic in config.get("kv", {}):
            config["kv"] = {args.topic: config["kv"][args.topic]}
            config["keywords"] = {args.topic: config["keywords"][args.topic]}
            logging.info(f"Filtered to single topic: {args.topic}")
        else:
            available = list(config.get("kv", {}).keys())
            logging.error(f"Topic '{args.topic}' not found. Available: {available}")
            sys.exit(1)

    # Extract topic_groups from config (or use defaults)
    topic_groups = load_topic_groups_from_config(config)
    config["topic_groups"] = topic_groups
    run(**config)
