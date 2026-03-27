import re
from typing import Any

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


def make_paper_record(date: str, title: str, authors: str, arxiv_id: str, code: str) -> dict[str, Any]:
    return {
        "date": str(date).replace("**", "").strip(),
        "title": str(title).replace("**", "").strip(),
        "authors": str(authors).replace("**", "").strip(),
        "arxiv_id": normalize_arxiv_id(arxiv_id),
        "pdf_url": f"{ARXIV_ABS_PREFIX}{normalize_arxiv_id(arxiv_id)}",
        "translate_url": f"{PAPERS_COOL_PREFIX}{normalize_arxiv_id(arxiv_id)}",
        "read_url": f"{HJFY_PREFIX}{normalize_arxiv_id(arxiv_id)}",
        "code_url": None if str(code).strip() == "null" else extract_link_target(str(code)),
    }


def extract_link_target(text: str) -> str | None:
    match = re.search(r"\((https?://[^)]+)\)", str(text))
    if match:
        return match.group(1)
    text = str(text).strip()
    return text if text.startswith("http://") or text.startswith("https://") else None


def parse_legacy_paper_row(row: str) -> dict[str, Any]:
    raw = str(row).strip()
    if raw.endswith("\n"):
        raw = raw[:-1]
    parts = raw.strip("|").split("|")
    if len(parts) < 5:
        raise ValueError(f"Unexpected row format: {row[:200]}")

    if len(parts) >= 7:
        date = parts[0]
        title = "|".join(parts[1:-6 + 1]).replace("**", "").strip() if len(parts) > 7 else parts[1]
        # Simpler and more reliable from the right.
        code = parts[-1]
        read = parts[-2]
        translate = parts[-3]
        pdf = parts[-4]
        authors = parts[-5]
        title = "|".join(parts[1:-5])
        record = make_paper_record(date, title, authors, normalize_arxiv_id(pdf), code)
        if extract_link_target(translate):
            record["translate_url"] = extract_link_target(translate)
        if extract_link_target(read):
            record["read_url"] = extract_link_target(read)
        return record

    date = parts[0]
    title = "|".join(parts[1:-3])
    authors = parts[-3]
    pdf = parts[-2]
    code = parts[-1]
    return make_paper_record(date, title, authors, normalize_arxiv_id(pdf), code)


def ensure_paper_record(entry: Any, paper_id: str | None = None) -> dict[str, Any]:
    if isinstance(entry, dict):
        arxiv_id = normalize_arxiv_id(entry.get("arxiv_id") or paper_id or entry.get("pdf_url", ""))
        record = {
            "date": str(entry.get("date", "")).replace("**", "").strip(),
            "title": str(entry.get("title", "")).replace("**", "").strip(),
            "authors": str(entry.get("authors", "")).replace("**", "").strip(),
            "arxiv_id": arxiv_id,
            "pdf_url": entry.get("pdf_url") or f"{ARXIV_ABS_PREFIX}{arxiv_id}",
            "translate_url": entry.get("translate_url") or f"{PAPERS_COOL_PREFIX}{arxiv_id}",
            "read_url": entry.get("read_url") or f"{HJFY_PREFIX}{arxiv_id}",
            "code_url": entry.get("code_url"),
        }
        return record
    return parse_legacy_paper_row(str(entry))


def render_paper_row(entry: Any, paper_id: str | None = None, emphasize: bool = False) -> str:
    record = ensure_paper_record(entry, paper_id=paper_id)
    date = f"**{record['date']}**" if emphasize else record["date"]
    title = f"**{record['title']}**" if emphasize else record["title"]
    code = "null"
    if record.get("code_url"):
        code = f"**[link]({record['code_url']})**" if emphasize else f"[link]({record['code_url']})"
    return (
        f"|{date}|{title}|{record['authors']}|"
        f"[{record['arxiv_id']}]({record['pdf_url']})|"
        f"[translate]({record['translate_url']})|"
        f"[read]({record['read_url']})|"
        f"{code}|\n"
    )
