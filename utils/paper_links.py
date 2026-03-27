import re

ARXIV_ABS_PREFIX = "https://arxiv.org/abs/"
PAPERS_COOL_PREFIX = "https://papers.cool/arxiv/"
HJFY_PREFIX = "https://hjfy.top/arxiv/"


def normalize_arxiv_id(arxiv_id_or_link: str) -> str:
    text = str(arxiv_id_or_link).strip()
    match = re.search(r"\[(\d{4}\.\d{4,5}(?:v\d+)?)\]", text)
    if match:
        arxiv_id = match.group(1)
    else:
        match = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", text)
        arxiv_id = match.group(1) if match else text
    return re.sub(r"v\d+$", "", arxiv_id)


def pdf_markdown(arxiv_id: str) -> str:
    return f"[{arxiv_id}]({ARXIV_ABS_PREFIX}{arxiv_id})"


def translate_markdown(arxiv_id: str) -> str:
    return f"[translate]({PAPERS_COOL_PREFIX}{arxiv_id})"


def read_markdown(arxiv_id: str) -> str:
    return f"[read]({HJFY_PREFIX}{arxiv_id})"


def render_paper_row(date: str, title: str, authors: str, arxiv_id: str, code: str) -> str:
    return (
        f"|{date}|{title}|{authors}|{pdf_markdown(arxiv_id)}|"
        f"{translate_markdown(arxiv_id)}|{read_markdown(arxiv_id)}|{code}|\n"
    )
