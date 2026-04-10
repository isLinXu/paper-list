import argparse
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pwc_archive import decode_github_readme, dump_json, enrich_with_github, load_json, record_path_iter


def is_rate_limited(response: requests.Response) -> bool:
    if response.status_code != 403:
        return False
    remaining = response.headers.get("X-RateLimit-Remaining")
    return remaining == "0" or "rate limit" in response.text.lower()


def fetch_github_repo(record: dict, api_base: str) -> tuple[dict, dict, dict, str]:
    owner = record.get("repo_owner")
    name = record.get("repo_name")
    if not owner or not name:
        raise ValueError("Record does not contain repo_owner/repo_name")

    headers = {
        "User-Agent": "paper-list/1.0",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repo_url = f"{api_base.rstrip('/')}/repos/{owner}/{name}"
    repo_response = requests.get(repo_url, headers=headers, timeout=30)
    if is_rate_limited(repo_response):
        raise requests.HTTPError(
            "GitHub API rate limit exceeded. Set GITHUB_TOKEN before rerunning pwc_enrich_github.py.",
            response=repo_response,
        )
    repo_response.raise_for_status()
    languages_response = requests.get(f"{repo_url}/languages", headers=headers, timeout=30)
    if is_rate_limited(languages_response):
        raise requests.HTTPError(
            "GitHub API rate limit exceeded while fetching languages. Set GITHUB_TOKEN before rerunning pwc_enrich_github.py.",
            response=languages_response,
        )
    languages_response.raise_for_status()
    readme_response = requests.get(f"{repo_url}/readme", headers=headers, timeout=30)
    readme_payload = {}
    if readme_response.status_code == 200:
        readme_payload = readme_response.json()
    elif is_rate_limited(readme_response):
        raise requests.HTTPError(
            "GitHub API rate limit exceeded while fetching README. Set GITHUB_TOKEN before rerunning pwc_enrich_github.py.",
            response=readme_response,
        )
    elif readme_response.status_code != 404:
        readme_response.raise_for_status()
    return repo_response.json(), languages_response.json(), readme_payload, repo_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich normalized PapersWithCode records with GitHub repository metadata.")
    parser.add_argument(
        "--input",
        default="data/pwc_archive/normalized/papers",
        help="Input JSON file or directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional separate output directory. Defaults to updating files in place.",
    )
    parser.add_argument("--api-base", default="https://api.github.com", help="GitHub API base URL.")
    args = parser.parse_args()

    for file_path in record_path_iter(args.input):
        record = load_json(file_path, {})
        if not record or not record.get("repo_owner") or not record.get("repo_name"):
            continue
        try:
            repo_payload, languages_payload, readme_payload, request_url = fetch_github_repo(record, args.api_base)
        except requests.RequestException as exc:
            print(f"GitHub request failed for {file_path.name}: {exc}")
            continue
        enriched = enrich_with_github(
            record,
            repo_payload,
            languages_payload,
            request_url,
            readme_text=decode_github_readme(readme_payload),
        )
        target = Path(args.output_dir) / file_path.name if args.output_dir else file_path
        dump_json(target, enriched)
        print(f"GitHub enriched {target}")


if __name__ == "__main__":
    main()
