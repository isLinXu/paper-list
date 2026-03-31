# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    _ensure_parent(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def write_meta(
    path: Path,
    topics: list[str],
    min_date: str,
    max_date: str,
    default_range_days: int = 90,
    default_range_months: int = 12,
) -> None:
    _ensure_parent(path)
    meta = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "topics": topics,
        "min_date": min_date,
        "max_date": max_date,
        "granularities": ["day", "month"],
        "default_range_days": int(default_range_days),
        "default_range_months": int(default_range_months),
    }
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

