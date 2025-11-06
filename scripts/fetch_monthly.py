import os
import sys
import logging
import argparse
import datetime
import calendar

# Ensure project root is at the front of sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.configs import load_config
from utils.get_infos import get_daily_papers
from utils.json_tools import json_to_md
from utils.updates import update_json_file

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)


def split_month_ranges(start_date_str: str, end_date_str: str):
    """Split an inclusive date range into month-bounded windows."""
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)

    ranges = []
    cur = start_date
    while cur <= end_date:
        last_day = calendar.monthrange(cur.year, cur.month)[1]
        month_end = datetime.date(cur.year, cur.month, last_day)
        window_end = min(month_end, end_date)
        ranges.append((cur, window_end))
        cur = window_end + datetime.timedelta(days=1)
    return ranges


def run_monthly(config_path: str):
    config = load_config(config_path)

    keywords = config['kv']
    max_results = int(config.get('max_results', 100))

    publish_readme = bool(config.get('publish_readme', True))
    publish_gitpage = bool(config.get('publish_gitpage', True))
    publish_wechat = bool(config.get('publish_wechat', False))
    show_badge = bool(config.get('show_badge', True))

    json_readme_path = config['json_readme_path']
    md_readme_path = config['md_readme_path']

    json_gitpage_path = config['json_gitpage_path']
    md_gitpage_path = config['md_gitpage_path']

    json_wechat_path = config.get('json_wechat_path', None)
    md_wechat_path = config.get('md_wechat_path', None)

    start_date = config['start_date']
    end_date = config['end_date']

    month_ranges = split_month_ranges(start_date, end_date)
    logging.info(f"Monthly windows: {[(s.isoformat(), e.isoformat()) for s, e in month_ranges]}")

    # Iterate daily within each month window to guarantee coverage
    for s_date, e_date in month_ranges:
        cur = s_date
        while cur <= e_date:
            day_str = cur.isoformat()
            logging.info(f"Fetching day {day_str}")
            data_collector = []
            data_collector_web = []
            for topic, keyword in keywords.items():
                data, data_web = get_daily_papers(topic, query=keyword, max_results=max_results,
                                                  start_date=day_str, end_date=day_str)
                data_collector.append(data)
                data_collector_web.append(data_web)

            # Merge JSON per day
            if publish_readme:
                update_json_file(json_readme_path, data_collector)
            if publish_gitpage:
                update_json_file(json_gitpage_path, data_collector)
            if publish_wechat and json_wechat_path:
                update_json_file(json_wechat_path, data_collector_web)

            cur += datetime.timedelta(days=1)

    # Render markdown once at the end
    if publish_readme:
        json_to_md(json_readme_path, md_readme_path, task='Update Readme',
                   to_web=False, show_badge=show_badge)
    if publish_gitpage:
        json_to_md(json_gitpage_path, md_gitpage_path, task='Update GitPage',
                   to_web=True, show_badge=show_badge, use_tc=False, use_b2t=False)
    if publish_wechat and json_wechat_path and md_wechat_path:
        json_to_md(json_wechat_path, md_wechat_path, task='Update Wechat',
                   to_web=False, use_title=False, show_badge=show_badge)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default='config.yaml',
                        help='configuration file path')
    args = parser.parse_args()
    run_monthly(args.config_path)