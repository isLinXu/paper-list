import datetime
import logging

import arxiv
import requests


base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
github_url = "https://api.github.com/search/repositories"
arxiv_url = "http://arxiv.org/"

def get_code_link(qword: str, github_url: str) -> str:
    """
    This short function was auto-generated by ChatGPT.
    I only renamed some params and added some comments.
    @param qword: query string, eg. arxiv ids and paper titles
    @return paper_code in github: string, if not found, return None
    """
    # query = f"arxiv:{arxiv_id}"
    query = f"{qword}"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc"
    }
    r = requests.get(github_url, params=params)
    results = r.json()
    code_link = None
    if results["total_count"] > 0:
        code_link = results["items"][0]["html_url"]
    return code_link

def get_authors(authors, first_author=False):
    output = str()
    if first_author == False:
        output = ", ".join(str(author) for author in authors)
    else:
        output = authors[0]
    return output



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

    search_engine = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    # today = datetime.date.today()
    # if end_date is None:
    #     end_date = today

    today = datetime.date.today()
    if end_date is None:
        end_date = today
    else:
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date is not None:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()

    for result in search_engine.results():
        publish_time = result.published.date()
        # print(f"publish_time = {publish_time}")
        if start_date and publish_time < start_date:
            continue
        if end_date and publish_time > end_date:
            continue

        paper_id = result.get_short_id()
        paper_title = result.title
        paper_url = result.entry_id
        code_url = base_url + paper_id  # TODO
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

        try:
            # source code link
            r = requests.get(code_url).json()
            repo_url = None
            if "official" in r and r["official"]:
                repo_url = r["official"]["url"]
            if repo_url is not None:
                content[paper_key] = "|**{}**|**{}**|{} et.al.|[{}]({})|**[link]({})**|\n".format(
                    update_time, paper_title, paper_first_author, paper_key, paper_url, repo_url)
                content_to_web[paper_key] = "- {}, **{}**, {} et.al., Paper: [{}]({}), Code: **[{}]({})**".format(
                    update_time, paper_title, paper_first_author, paper_url, paper_url, repo_url, repo_url)

            else:
                content[paper_key] = "|**{}**|**{}**|{} et.al.|[{}]({})|null|\n".format(
                    update_time, paper_title, paper_first_author, paper_key, paper_url)
                content_to_web[paper_key] = "- {}, **{}**, {} et.al., Paper: [{}]({})".format(
                    update_time, paper_title, paper_first_author, paper_url, paper_url)

            # TODO: select useful comments
            comments = None
            if comments != None:
                content_to_web[paper_key] += f", {comments}\n"
            else:
                content_to_web[paper_key] += f"\n"

        except Exception as e:
            logging.error(f"exception: {e} with id: {paper_key}")

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