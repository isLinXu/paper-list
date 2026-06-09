import os
import datetime
import logging
import time
import re
from urllib.parse import quote

import arxiv
import requests

from .paper_links import ARXIV_ABS_PREFIX, make_paper_record

github_url = "https://api.github.com/search/repositories"


def sanitize_table_cell(value: str) -> str:
    """Keep markdown table rows parseable even when metadata contains pipes."""
    return str(value).replace("|", " | ").replace("\n", " ").strip()

def get_code_link(qword: str, github_url: str) -> str:
    """
    @param qword: query string, eg. arxiv ids and paper titles
    @return paper_code in github: string, if not found, return None
    """
    query = f"{qword}"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc"
    }
    headers = {'User-Agent': 'paper-list/1.0'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'token {token}'
    r = requests.get(github_url, params=params, timeout=4, headers=headers)
    results = r.json()
    code_link = None
    if results.get("total_count", 0) > 0:
        code_link = results["items"][0]["html_url"]
    return code_link

def get_authors(authors, first_author=False):
    output = str()
    if first_author == False:
        output = ", ".join(str(author) for author in authors)
    else:
        output = authors[0]
    return output


def try_hf_repo(arxiv_id: str) -> str | None:
    """Attempt to extract a GitHub repo URL from Hugging Face papers page.

    NOTE: HuggingFace connection is unstable and causes timeouts in
    GitHub Actions. This function is disabled until a reliable
    alternative (e.g. async with retry + timeout) is implemented.
    """
    return None


def get_daily_papers(topic, query="slam", max_results=2, start_date=None, end_date=None):
    """Fetch papers from arXiv for a given topic and date range.

    GitHub code-link lookup is intentionally NOT performed here.
    Code URLs are enriched separately by ``update_paper_links`` (weekly job)
    to avoid blocking the fast daily-fetch path.

    @param topic: str
    @param query: str
    @param start_date: str YYYY-MM-DD or None
    @param end_date: str YYYY-MM-DD or None
    @return (data, data_web): dicts keyed by topic
    """
    logging.debug(f"get_daily_papers: topic={topic!r} start_date={start_date} end_date={end_date}")
    # output
    content = dict()
    content_to_web = dict()

    logging.info(f"Executing arXiv search for topic '{topic}' with query: {query}")

    # log expected first-page URL for debugging
    encoded_query = quote(query)
    preview_url = (
        f"https://export.arxiv.org/api/query?search_query={encoded_query}&id_list=&sortBy=submittedDate&sortOrder=descending&start=0&max_results={int(max_results)}"
    )
    logging.info(f"arXiv preview URL: {preview_url}")

    # use client with retries to avoid EmptyPage error
    client = arxiv.Client(page_size=int(max_results), delay_seconds=10, num_retries=10)

    search_engine = arxiv.Search(
        query=query,
        max_results=int(max_results),
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    today = datetime.date.today()
    if end_date is None:
        end_date = today
    else:
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date is not None:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()

    result_count = 0

    def iterate_results(arxiv_client: arxiv.Client, arxiv_search: arxiv.Search):
        nonlocal result_count
        for result in arxiv_client.results(arxiv_search):
            publish_time = result.published.date()
            # date window filter
            if start_date and publish_time < start_date:
                continue
            if end_date and publish_time > end_date:
                continue

            result_count += 1

            paper_id = result.get_short_id()
            paper_title = sanitize_table_cell(result.title)
            paper_authors = get_authors(result.authors)
            paper_first_author = sanitize_table_cell(get_authors(result.authors, first_author=True))
            update_time = result.updated.date()

            logging.info(f"Time = {update_time} title = {paper_title} author = {paper_first_author}")

            # eg: 2108.09112v1 -> 2108.09112
            ver_pos = paper_id.find('v')
            paper_key = paper_id[0:ver_pos] if ver_pos != -1 else paper_id

            # code_url is left as None here; it will be filled later by
            # update_paper_links (weekly job) using cached GitHub API results.
            content[paper_key] = make_paper_record(
                publish_time,
                paper_title,
                f"{paper_first_author} et.al.",
                paper_key,
                "null",
            )
            content_to_web[paper_key] = "- {}, **{}**, {} et.al., Paper: [{}]({})".format(
                publish_time, paper_title, paper_first_author,
                ARXIV_ABS_PREFIX + paper_key,
                ARXIV_ABS_PREFIX + paper_key)

    try:
        iterate_results(client, search_engine)
    except arxiv.UnexpectedEmptyPageError as e:
        logging.warning(f"UnexpectedEmptyPageError with page_size={int(max_results)}; falling back to smaller page size. error={e}")
        # fallback to smaller pagination to avoid start=25 empty page
        small_page_size = 25
        client_small = arxiv.Client(page_size=small_page_size, delay_seconds=3, num_retries=3)
        search_small = arxiv.Search(
            query=query,
            max_results=int(max_results),
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        try:
            iterate_results(client_small, search_small)
        except Exception as e2:
            logging.error(f"Fallback client also failed: {e2}")
    except Exception as e:
        logging.error(f"arxiv client results error: {e}")

    logging.info(f"arXiv search returned {result_count} items for topic '{topic}'")

    data = {topic: content}
    data_web = {topic: content_to_web}
    return data, data_web


def get_papers_in_date_range(topic, query="slam", max_results=2, start_date=None, end_date=None):
    """Fetch papers within a date range using a single arXiv API call.

    Unlike the previous day-by-day loop, this issues one request with an
    expanded max_results budget and filters by date on the Python side,
    which is significantly more efficient.
    """
    if start_date is None or end_date is None:
        raise ValueError("Start date and end date must be provided")

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    date_span = (end_dt - start_dt).days + 1

    # Scale max_results by the date span so we don't under-fetch
    scaled_max = max_results * max(date_span, 1)

    data, data_web = get_daily_papers(
        topic, query=query,
        max_results=scaled_max,
        start_date=start_date,
        end_date=end_date,
    )
    return [data]
