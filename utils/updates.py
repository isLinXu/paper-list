import datetime
import json
import logging
import os

import requests

from .paper_links import ensure_paper_record

HF_PAPER_PAGE = "https://huggingface.co/papers/"
github_url = "https://api.github.com/search/repositories"


def parse_arxiv_record(entry, paper_id=None):
    record = ensure_paper_record(entry, paper_id=paper_id)
    return (
        record["date"],
        record["title"],
        record["authors"],
        record["arxiv_id"],
        record["translate_url"],
        record["read_url"],
        record["code_url"],
    )


def update_paper_links(filename, start_date=None, end_date=None):
    """
    Weekly update paper links in json file using GitHub fallback when needed.
    """

    def try_hf_repo(arxiv_id: str) -> str | None:
        # Hugging Face connection is unstable and causes timeouts.
        # Disabling it to rely on GitHub API which is more stable.
        return None

    with open(filename, "r") as f:
        content = f.read()
        if not content:
            data = {}
        else:
            data = json.loads(content)

    start_bound = datetime.date.fromisoformat(start_date) if start_date else None
    end_bound = datetime.date.fromisoformat(end_date) if end_date else None

    for keyword, papers in data.items():
        logging.info(f"keywords = {keyword}")
        for paper_id, entry in list(papers.items()):
            record = ensure_paper_record(entry, paper_id=paper_id)
            publish_date = datetime.date.fromisoformat(record["date"])

            if start_bound and publish_date < start_bound:
                continue
            if end_bound and publish_date > end_bound:
                continue

            if record.get("code_url"):
                papers[paper_id] = record
                continue

            repo_url = try_hf_repo(record["arxiv_id"])
            if repo_url is None:
                try:
                    params = {
                        "q": f"arxiv:{record['arxiv_id']} {record['title']}",
                        "sort": "stars",
                        "order": "desc",
                    }
                    headers = {"User-Agent": "paper-list/1.0"}
                    token = os.environ.get("GITHUB_TOKEN")
                    if token:
                        headers["Authorization"] = f"token {token}"
                    response = requests.get(github_url, params=params, timeout=4, headers=headers)
                    if response.ok and "application/json" in (response.headers.get("Content-Type") or ""):
                        payload = response.json()
                        if payload.get("total_count", 0) > 0:
                            repo_url = payload["items"][0]["html_url"]
                except Exception as exc:
                    logging.info(f"GitHub fallback no result for id {record['arxiv_id']}: {exc}")

            if repo_url is not None:
                record["code_url"] = repo_url
            papers[paper_id] = record

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def update_json_file(filename, data_dict):
    """
    Daily update json file using data_dict.
    """
    with open(filename, "r") as f:
        content = f.read()
        if not content:
            data = {}
        else:
            data = json.loads(content)

    for chunk in data_dict:
        for keyword, papers in chunk.items():
            normalized = {
                paper_id: ensure_paper_record(entry, paper_id=paper_id)
                for paper_id, entry in papers.items()
            }
            if keyword in data:
                existing = {
                    paper_id: ensure_paper_record(entry, paper_id=paper_id)
                    for paper_id, entry in data[keyword].items()
                }
                existing.update(normalized)
                data[keyword] = existing
            else:
                data[keyword] = normalized

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def normalize_json_rows(filename):
    with open(filename, "r") as f:
        content = f.read()
        if not content:
            return
        data = json.loads(content)

    normalized = {}
    for keyword, papers in data.items():
        normalized[keyword] = {
            paper_id: ensure_paper_record(entry, paper_id=paper_id)
            for paper_id, entry in papers.items()
        }

    with open(filename, "w") as f:
        json.dump(normalized, f, indent=4)
