import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from utils.configs import load_config
from utils.json_tools import json_to_md, load_topic_groups_from_config

json_file = './docs/data'
show_badge = True

# Load topic_groups from config if available
try:
    config = load_config('config.yaml')
    topic_groups = load_topic_groups_from_config(config)
except Exception:
    topic_groups = None

if os.path.exists(json_file):
    # Generate README.md
    json_to_md(
        json_file,
        'README.md',
        task='Update Readme',
        show_badge=show_badge,
        split_to_docs=True,
        page_variant='readme',
        topic_groups=topic_groups,
    )
    # Generate docs/index.md for GitHub Pages
    json_to_md(
        json_file,
        './docs/index.md',
        task='Update GitPage',
        to_web=True,
        show_badge=show_badge,
        use_tc=True,
        use_b2t=False,
        split_to_docs=True,
        page_variant='home',
        topic_groups=topic_groups,
    )
    # Generate docs/paper_list.md for the dense GitHub Pages catalog view
    json_to_md(
        json_file,
        './docs/paper_list.md',
        task='Update Full Catalog',
        to_web=True,
        show_badge=False,
        use_tc=True,
        use_b2t=False,
        split_to_docs=False,
        page_variant='catalog',
        topic_groups=topic_groups,
    )
    print("Regenerated README.md, docs/index.md, docs/paper_list.md, and split docs.")
else:
    print(f"Error: {json_file} not found.")
