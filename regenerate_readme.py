import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from utils.json_tools import json_to_md

json_file = './docs/paper_list.json'
md_file = 'README.md'
show_badge = True

if os.path.exists(json_file):
    json_to_md(json_file, md_file, task='Update Readme', show_badge=show_badge, split_to_docs=True)
    print("Regenerated README.md and split docs.")
else:
    print(f"Error: {json_file} not found.")
