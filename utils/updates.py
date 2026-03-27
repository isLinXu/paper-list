import os
import json
import logging
import re
import datetime

import requests

from .paper_links import normalize_arxiv_id, render_paper_row

HF_PAPER_PAGE = "https://huggingface.co/papers/"
github_url = "https://api.github.com/search/repositories"

def parse_arxiv_record(s: str):
    row = str(s).strip()
    if row.endswith("\n"):
        row = row[:-1]
    row = row.strip("|")
    parts = row.split("|")
    if len(parts) < 5:
        raise ValueError(f"Unexpected row format: {s[:200]}")

    date = parts[0].replace("**", "").strip()
    code = parts[-1].strip()
    if len(parts) >= 7:
        read_link = parts[-2].strip()
        translate_link = parts[-3].strip()
        arxiv_id_link = parts[-4].strip()
        authors = parts[-5].replace("**", "").strip()
        title = "|".join(parts[1:-5]).replace("**", "").strip()
    else:
        read_link = None
        translate_link = None
        arxiv_id_link = parts[-2].strip()
        authors = parts[-3].replace("**", "").strip()
        title = "|".join(parts[1:-3]).replace("**", "").strip()
    return date, title, authors, arxiv_id_link, translate_link, read_link, code


def update_paper_links(filename, start_date=None, end_date=None):
    '''
    Weekly update paper links in json file using Hugging Face papers page
    with GitHub fallback when needed.
    '''

    def try_hf_repo(arxiv_id: str) -> str | None:
        # Hugging Face connection is unstable and causes timeouts.
        # Disabling it to rely on GitHub API which is more stable.
        return None
        url = HF_PAPER_PAGE + arxiv_id
        try:
            r = requests.get(url, timeout=4, headers={'User-Agent': 'paper-list/1.0'})
            if not r.ok:
                logging.info(f"HF page non-200 for {arxiv_id}: {r.status_code}")
                return None
            ct = r.headers.get('Content-Type') or ''
            if 'text/html' not in ct:
                logging.info(f"HF page non-HTML for {arxiv_id}: ct={ct}")
                return None
            # find first GitHub repository link
            m = re.search(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r.text)
            if m:
                return m.group(0)
        except requests.exceptions.RequestException as e:
            logging.info(f"HF request error for {arxiv_id}: {e}")
        except Exception as e:
            logging.info(f"HF unexpected error for {arxiv_id}: {e}")
        return None

    with open(filename, "r") as f:
        content = f.read()
        if not content:
            m = {}
        else:
            m = json.loads(content)

    json_data = m.copy()
    start_bound = datetime.date.fromisoformat(start_date) if start_date else None
    end_bound = datetime.date.fromisoformat(end_date) if end_date else None

    for keywords, v in json_data.items():
        logging.info(f'keywords = {keywords}')
        for paper_id, contents in v.items():
            contents = str(contents)

            try:
                update_time, paper_title, paper_first_author, arxiv_id_link, _, _, code_url = parse_arxiv_record(contents)
            except ValueError as exc:
                logging.warning(f"Skip unparsable record {paper_id}: {exc}")
                continue

            publish_date = datetime.date.fromisoformat(update_time)
            if start_bound and publish_date < start_bound:
                continue
            if end_bound and publish_date > end_bound:
                continue

            arxiv_id = normalize_arxiv_id(arxiv_id_link)

            contents = render_paper_row(update_time, paper_title, paper_first_author, arxiv_id, code_url)
            json_data[keywords][paper_id] = str(contents)
            logging.info(f'paper_id = {paper_id}, contents = {contents}')

            valid_link = False if '|null|' in contents else True
            if valid_link:
                continue

            repo_url = try_hf_repo(arxiv_id)
            if repo_url is None:
                # fallback to GitHub search by arxiv id + title
                try:
                    params = {"q": f"arxiv:{arxiv_id} {paper_title}", "sort": "stars", "order": "desc"}
                    headers = {'User-Agent': 'paper-list/1.0'}
                    token = os.environ.get('GITHUB_TOKEN')
                    if token:
                        headers['Authorization'] = f'token {token}'
                    gr = requests.get(github_url, params=params, timeout=4, headers=headers)
                    if gr.ok and 'application/json' in (gr.headers.get('Content-Type') or ''):
                        gj = gr.json()
                        if gj.get("total_count", 0) > 0:
                            repo_url = gj["items"][0]["html_url"]
                except Exception as e:
                    logging.info(f"GitHub fallback no result for id {arxiv_id}: {e}")

            if repo_url is not None:
                new_cont = contents.replace('|null|', f'|**[link]({repo_url})**|')
                logging.info(f'ID = {paper_id}, contents = {new_cont}')
                json_data[keywords][paper_id] = str(new_cont)

    # dump to json file
    with open(filename, "w") as f:
        json.dump(json_data, f, indent=4)

def update_json_file(filename, data_dict):
    '''
    daily update json file using data_dict
    '''
    with open(filename, "r") as f:
        content = f.read()
        if not content:
            m = {}
        else:
            m = json.loads(content)

    json_data = m.copy()

    # update papers in each keywords
    for data in data_dict:
        for keyword in data.keys():
            papers = data[keyword]

            if keyword in json_data.keys():
                json_data[keyword].update(papers)
            else:
                json_data[keyword] = papers

    with open(filename, "w") as f:
        json.dump(json_data, f, indent=4)


def normalize_json_rows(filename):
    with open(filename, "r") as f:
        content = f.read()
        if not content:
            return
        json_data = json.loads(content)

    for keyword, papers in json_data.items():
        for paper_id, row in list(papers.items()):
            date, title, authors, arxiv_id_link, _, _, code = parse_arxiv_record(str(row))
            arxiv_id = normalize_arxiv_id(arxiv_id_link)
            json_data[keyword][paper_id] = render_paper_row(date, title, authors, arxiv_id, code)

    with open(filename, "w") as f:
        json.dump(json_data, f, indent=4)
