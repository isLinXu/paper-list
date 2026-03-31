# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

import datetime as _dt
from collections import Counter
from typing import Any, Iterator


def _iter_records(store: dict[str, dict[str, Any]] | None) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """
    Iterate (topic, paper_id, record) from store.

    Expected store shape:
      {topic: {paper_id: {"date": "YYYY-MM-DD", ...}, ...}, ...}
    """

    for topic, papers in (store or {}).items():
        for paper_id, record in (papers or {}).items():
            if not isinstance(record, dict):
                continue
            date = str(record.get("date", "")).strip()
            if not date:
                continue
            yield topic, str(paper_id), record


def _month_of(date_str: str) -> str:
    # date_str: YYYY-MM-DD -> YYYY-MM
    return str(date_str)[:7]


def parse_first_author(authors_field: str) -> str:
    text = str(authors_field or "").strip()
    if not text:
        return ""
    # normalize common suffixes
    for token in [" et.al.", " et al.", " et.al", " et al"]:
        if token in text:
            text = text.split(token)[0].strip()
            break
    return text


def aggregate_daily_counts(store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for topic, _, record in _iter_records(store):
        day = str(record["date"])
        counts[(topic, day)] += 1
    rows = [{"topic": t, "date": d, "count": c} for (t, d), c in counts.items()]
    rows.sort(key=lambda r: (r["topic"], r["date"]))
    return rows


def aggregate_monthly_counts(store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for topic, _, record in _iter_records(store):
        month = _month_of(record["date"])
        counts[(topic, month)] += 1
    rows = [{"topic": t, "date": m, "count": c} for (t, m), c in counts.items()]
    rows.sort(key=lambda r: (r["topic"], r["date"]))
    return rows


def aggregate_code_coverage_daily(store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    totals: Counter[tuple[str, str]] = Counter()
    covered: Counter[tuple[str, str]] = Counter()
    for topic, _, record in _iter_records(store):
        day = str(record["date"])
        totals[(topic, day)] += 1
        if record.get("code_url"):
            covered[(topic, day)] += 1

    rows: list[dict[str, Any]] = []
    for (topic, day), total in totals.items():
        c = covered.get((topic, day), 0)
        rows.append(
            {
                "topic": topic,
                "date": day,
                "total": int(total),
                "code_covered": int(c),
                "code_coverage": round(c / total, 4) if total else None,
            }
        )
    rows.sort(key=lambda r: (r["topic"], r["date"]))
    return rows


def aggregate_code_coverage_monthly(store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    totals: Counter[tuple[str, str]] = Counter()
    covered: Counter[tuple[str, str]] = Counter()
    for topic, _, record in _iter_records(store):
        month = _month_of(record["date"])
        totals[(topic, month)] += 1
        if record.get("code_url"):
            covered[(topic, month)] += 1

    rows: list[dict[str, Any]] = []
    for (topic, month), total in totals.items():
        c = covered.get((topic, month), 0)
        rows.append(
            {
                "topic": topic,
                "date": month,
                "total": int(total),
                "code_covered": int(c),
                "code_coverage": round(c / total, 4) if total else None,
            }
        )
    rows.sort(key=lambda r: (r["topic"], r["date"]))
    return rows


def _in_range(date_str: str, start_date: str | None, end_date: str | None) -> bool:
    try:
        d = _dt.date.fromisoformat(date_str)
    except ValueError:
        return False

    if start_date:
        try:
            if d < _dt.date.fromisoformat(start_date):
                return False
        except ValueError:
            return False

    if end_date:
        try:
            if d > _dt.date.fromisoformat(end_date):
                return False
        except ValueError:
            return False

    return True


def aggregate_top_first_authors(
    store: dict[str, dict[str, Any]],
    start_date: str,
    end_date: str,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for _, _, record in _iter_records(store):
        if not _in_range(record["date"], start_date, end_date):
            continue
        author = parse_first_author(record.get("authors", ""))
        if author:
            counter[author] += 1
    rows = [
        {"author": a, "count": int(c), "rank": i + 1}
        for i, (a, c) in enumerate(counter.most_common(top_n))
    ]
    return rows


def aggregate_topic_rank(
    store: dict[str, dict[str, Any]],
    start_date: str,
    end_date: str,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for topic, _, record in _iter_records(store):
        if not _in_range(record["date"], start_date, end_date):
            continue
        counter[topic] += 1
    rows = [{"topic": t, "count": int(c), "rank": i + 1} for i, (t, c) in enumerate(counter.most_common(top_n))]
    return rows

