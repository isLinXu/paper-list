
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
from utils.json_tools import json_to_md
from utils.updates import update_paper_links, update_json_file

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)

base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
github_url = "https://api.github.com/search/repositories"
arxiv_url = "https://arxiv.org/"

def run(**config):
    # TODO: use config
    data_collector = []
    data_collector_web = []

    keywords = config['kv']
    max_results = config['max_results']
    publish_readme = config['publish_readme']
    publish_gitpage = config['publish_gitpage']
    publish_wechat = config['publish_wechat']
    show_badge = config['show_badge']

    b_update = config['update_paper_links']
    logging.info(f'Update Paper Link = {b_update}')
    if config['update_paper_links'] == False:
        logging.info(f"GET daily papers begin")
        for topic, keyword in keywords.items():
            logging.info(f"Keyword: {topic}")
            data, data_web = get_daily_papers(topic, query=keyword, max_results=max_results,
                                              start_date=config['start_date'], end_date=config['end_date'])
            data_collector.append(data)
            data_collector_web.append(data_web)
            print("\n")
        logging.info(f"GET daily papers end")

    # 1. update README.md file
    if publish_readme:
        json_file = config['json_readme_path']
        md_file = config['md_readme_path']
        # update paper links
        if config['update_paper_links']:
            update_paper_links(json_file)
        else:
            # update json data
            update_json_file(json_file, data_collector)
        # json data to markdown
        json_to_md(json_file, md_file, task='Update Readme',
                   show_badge=show_badge, split_to_docs=True)

    # 2. update docs/index.md file (to gitpage)
    if publish_gitpage:
        json_file = config['json_gitpage_path']
        md_file = config['md_gitpage_path']
        # TODO: duplicated update paper links!!!
        if config['update_paper_links']:
            update_paper_links(json_file)
        else:
            update_json_file(json_file, data_collector)
        json_to_md(json_file, md_file, task='Update GitPage',
                   to_web=True, show_badge=show_badge,
                   use_tc=False, use_b2t=False)

    # 3. Update docs/wechat.md file
    if publish_wechat:
        json_file = config['json_wechat_path']
        md_file = config['md_wechat_path']
        # TODO: duplicated update paper links!!!
        if config['update_paper_links']:
            update_paper_links(json_file)
        else:
            update_json_file(json_file, data_collector_web)
        json_to_md(json_file, md_file, task='Update Wechat', to_web=False, use_title=False, show_badge=show_badge)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default='config.yaml',
                        help='configuration file path')
    parser.add_argument('--update_paper_links', default=False,
                        action="store_true", help='whether to update paper links etc.')
    args = parser.parse_args()
    config = load_config(args.config_path)
    config = {**config, 'update_paper_links': args.update_paper_links}
    run(**config)