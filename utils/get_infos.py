import datetime
import logging
import time
import re
from urllib.parse import quote

import arxiv
import requests


HF_PAPER_PAGE = "https://huggingface.co/papers/"
github_url = "https://api.github.com/search/repositories"
arxiv_url = "https://arxiv.org/"

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
    r = requests.get(github_url, params=params, timeout=4, headers={'User-Agent': 'paper-list/1.0'})
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
    """Attempt to extract a GitHub repo URL from Hugging Face papers page."""
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


def get_daily_papers(topic, query="slam", max_results=2, start_date=None, end_date=None):
    print(f"start_date = {start_date}, end_date = {end_date}")
    """
    @param topic: str
    @param query: str
    @param start_date: datetime.date
    @param end_date: datetime.date
    @return paper_with_code: dict
    """
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
    client = arxiv.Client(page_size=int(max_results), delay_seconds=3, num_retries=3)

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
            paper_title = result.title
            paper_url = result.entry_id
            paper_abstract = result.summary.replace("\n", " ")
            paper_authors = get_authors(result.authors)
            paper_first_author = get_authors(result.authors, first_author=True)
            primary_category = result.primary_category
            update_time = result.updated.date()
            comments = result.comment

            logging.info(f"Time = {update_time} title = {paper_title} author = {paper_first_author}")

            # eg: 2108.09112v1 -> 2108.09112
            ver_pos = paper_id.find('v')
            if ver_pos == -1:
                paper_key = paper_id
            else:
                paper_key = paper_id[0:ver_pos]
            paper_url = arxiv_url + 'abs/' + paper_key

            # Try Hugging Face papers page -> GitHub fallback
            repo_url = try_hf_repo(paper_key)
            if repo_url is None:
                # fallback to GitHub search
                qword = f"arxiv:{paper_key} {paper_title}"
                try:
                    repo_url = get_code_link(qword, github_url)
                    if repo_url:
                        logging.info(f"GitHub fallback found repo for {paper_key}: {repo_url}")
                except Exception as e:
                    logging.info(f"GitHub fallback no result for id {paper_key}: {e}")

            if repo_url is not None:
                content[paper_key] = "|**{}**|**{}**|{} et.al.|[{}]({})|**[link]({})**|\n".format(
                    publish_time, paper_title, paper_first_author, paper_key, paper_url, repo_url)
                content_to_web[paper_key] = "- {}, **{}**, {} et.al., Paper: [{}]({}), Code: **[{}]({})**".format(
                    publish_time, paper_title, paper_first_author, paper_url, paper_url, repo_url, repo_url)
            else:
                content[paper_key] = "|**{}**|**{}**|{} et.al.|[{}]({})|null|\n".format(
                    publish_time, paper_title, paper_first_author, paper_key, paper_url)
                content_to_web[paper_key] = "- {}, **{}**, {} et.al., Paper: [{}]({})".format(
                    publish_time, paper_title, paper_first_author, paper_url, paper_url)

            # TODO: select useful comments
            comments = None
            if comments != None:
                content_to_web[paper_key] += f", {comments}\n"
            else:
                content_to_web[paper_key] += f"\n"

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
    if start_date is None or end_date is None:
        raise ValueError("Start date and end date must be provided")

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    current_date = start_date
    all_papers = []
    while current_date <= end_date:
        daily_papers, _ = get_daily_papers(topic, query=query, max_results=max_results, start_date=current_date, end_date=current_date)
        all_papers.append(daily_papers)
        current_date += datetime.timedelta(days=1)

    return all_papers