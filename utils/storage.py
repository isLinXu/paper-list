import json
from pathlib import Path

from .paper_links import ensure_paper_record


def load_paper_store(store_path: str | Path) -> dict:
    path = Path(store_path)
    if path.is_dir():
        merged = {}
        for year_file in sorted(path.glob("*.json")):
            chunk = json.loads(year_file.read_text()) if year_file.read_text().strip() else {}
            for topic, papers in chunk.items():
                topic_bucket = merged.setdefault(topic, {})
                for paper_id, entry in papers.items():
                    topic_bucket[paper_id] = ensure_paper_record(entry, paper_id=paper_id)
        return merged

    if not path.exists():
        return {}

    content = path.read_text()
    if not content.strip():
        return {}
    data = json.loads(content)
    normalized = {}
    for topic, papers in data.items():
        normalized[topic] = {
            paper_id: ensure_paper_record(entry, paper_id=paper_id)
            for paper_id, entry in papers.items()
        }
    return normalized


def save_paper_store(store_path: str | Path, data: dict) -> None:
    path = Path(store_path)
    if path.suffix == ".json":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=4))
        return

    path.mkdir(parents=True, exist_ok=True)
    yearly = {}
    for topic, papers in data.items():
        for paper_id, entry in papers.items():
            record = ensure_paper_record(entry, paper_id=paper_id)
            year = record["date"][:4]
            year_bucket = yearly.setdefault(year, {})
            topic_bucket = year_bucket.setdefault(topic, {})
            topic_bucket[paper_id] = record

    existing = {p.name for p in path.glob("*.json")}
    target = {f"{year}.json" for year in yearly}
    for stale in existing - target:
        (path / stale).unlink()

    for year, chunk in yearly.items():
        (path / f"{year}.json").write_text(json.dumps(chunk, indent=4))
