"""Shared constants and pure data helpers for catalog generation."""

from urllib.parse import urlparse

from utils.pwc_archive import slugify


FACET_SPECS = [
    {
        "field": "tasks",
        "label": "Tasks",
        "title": "Task Atlas",
        "description": "Browse the archive slice by research task and benchmark intent.",
        "directory": "tasks",
    },
    {
        "field": "methods",
        "label": "Methods",
        "title": "Method Atlas",
        "description": "Track methods, strategies, and algorithmic families extracted from papers and code.",
        "directory": "methods",
    },
    {
        "field": "architecture",
        "label": "Architectures",
        "title": "Architecture Atlas",
        "description": "Survey structural model families inferred from titles, abstracts, and repositories.",
        "directory": "architectures",
    },
    {
        "field": "frameworks",
        "label": "Frameworks",
        "title": "Framework Atlas",
        "description": "Review implementation stacks and runtime ecosystems tied to archived code.",
        "directory": "frameworks",
    },
    {
        "field": "datasets",
        "label": "Datasets",
        "title": "Dataset Atlas",
        "description": "Browse named datasets surfaced by parsing, repository hints, and metadata enrichment.",
        "directory": "datasets",
    },
    {
        "field": "benchmarks",
        "label": "Benchmarks",
        "title": "Benchmark Atlas",
        "description": "Track benchmark labels and evaluation slices preserved alongside archive-backed records.",
        "directory": "benchmarks",
    },
]


def short_domain(url: str) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.replace("www.", "")


def truncate_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown authors"
    if len(authors) <= 4:
        return ", ".join(authors)
    return ", ".join(authors[:4]) + f" +{len(authors) - 4}"


def count_records_with(records: list[dict], field: str) -> int:
    return sum(1 for record in records if record.get(field))


def bucket_counts(records: list[dict], field: str, limit: int = 4) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for record in records:
        for value in record.get(field) or []:
            label = str(value).strip()
            if not label:
                continue
            counts[label] = counts.get(label, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    return ranked[:limit]


def group_records_by_field(records: list[dict], field: str) -> list[tuple[str, list[dict]]]:
    groups: dict[str, list[dict]] = {}
    for record in records:
        for value in record.get(field) or []:
            label = str(value).strip()
            if not label:
                continue
            groups.setdefault(label, []).append(record)
    return sorted(groups.items(), key=lambda item: (-len(item[1]), item[0].lower()))


def facet_link(field: str, value: str, page_prefix: str = "") -> str:
    directory = next(spec["directory"] for spec in FACET_SPECS if spec["field"] == field)
    return f"{page_prefix}{directory}/{slugify(value)}.html"


def facet_index_link(field: str, page_prefix: str = "") -> str:
    directory = next(spec["directory"] for spec in FACET_SPECS if spec["field"] == field)
    return f"{page_prefix}{directory}/"
