# Analytics（可视化 + 导出 + 交互页）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 `docs/data/*.json` 生成 analytics 聚合数据（JSON/CSV）、静态图（PNG）、并在 GitHub Pages（Jekyll）下新增一个可交互的 `docs/analytics/` 页面，同时在 README / docs 首页加入入口与静态图嵌入。

**Architecture:** 离线聚合（Python）→ 产物落盘到 `docs/analytics/data` 与 `docs/analytics/charts`；交互页（纯 HTML/JS）读取预计算 JSON 进行前端筛选与绘图；工作流（GitHub Actions）在抓取更新后追加 analytics 构建并提交产物。

**Tech Stack:** Python 3.10、matplotlib（静态图）、标准库 csv/json/unittest、GitHub Pages(Jekyll)、Chart.js（交互页本地 vendored 静态文件）

---

## 0) Files to touch（文件结构锁定）

**Create:**
- `scripts/build_analytics.py`
- `utils/analytics/__init__.py`
- `utils/analytics/aggregate.py`
- `utils/analytics/export.py`
- `utils/analytics/charts.py`
- `tests/test_analytics.py`
- `docs/analytics/index.html`
- `docs/analytics/assets/app.css`
- `docs/analytics/assets/app.js`
- `docs/analytics/assets/vendor/chart.umd.min.js`
- `docs/analytics/.gitkeep`（可选，确保目录存在）

**Modify:**
- `requirements.txt`（加入 matplotlib）
- `utils/json_tools.py`（为 README 与 docs/index 注入 Analytics 入口与图表嵌入）
- `.github/workflows/paper-list.yml`（跑 analytics 构建 + 提交 docs/analytics/**）
- `.github/workflows/update_paper_links.yml`（同上）
- `README.md`（可选：补充 Analytics 使用说明；若由脚本生成则改 `utils/json_tools.py`）

---

### Task 1: 增加依赖与测试骨架

**Files:**
- Modify: `requirements.txt`
- Create: `tests/test_analytics.py`

- [ ] **Step 1: 在 requirements.txt 增加 matplotlib**

将 `requirements.txt` 更新为：

```txt
requests>=2.31.0
arxiv>=2.1.0
pyyaml>=6.0
matplotlib>=3.8.0
```

- [ ] **Step 2: 创建 tests 目录与 unittest 测试文件（先写失败测试）**

创建 `tests/test_analytics.py`：

```python
import unittest

from utils.analytics.aggregate import (
    aggregate_daily_counts,
    aggregate_monthly_counts,
    aggregate_code_coverage_daily,
    parse_first_author,
    aggregate_top_first_authors,
)


class TestAnalyticsAggregate(unittest.TestCase):
    def setUp(self):
        # 极小样例：2 个 topic，跨 2 天，含/不含 code_url
        self.store = {
            "LLM": {
                "2401.00001": {
                    "date": "2026-03-01",
                    "title": "t1",
                    "authors": "Alice Zhang et.al.",
                    "arxiv_id": "2401.00001",
                    "pdf_url": "https://arxiv.org/abs/2401.00001",
                    "translate_url": "https://papers.cool/arxiv/2401.00001",
                    "read_url": "https://hjfy.top/arxiv/2401.00001",
                    "code_url": "https://github.com/a/b",
                },
                "2401.00002": {
                    "date": "2026-03-01",
                    "title": "t2",
                    "authors": "Bob Li et.al.",
                    "arxiv_id": "2401.00002",
                    "pdf_url": "https://arxiv.org/abs/2401.00002",
                    "translate_url": "https://papers.cool/arxiv/2401.00002",
                    "read_url": "https://hjfy.top/arxiv/2401.00002",
                    "code_url": None,
                },
            },
            "Multimodal": {
                "2401.00003": {
                    "date": "2026-03-02",
                    "title": "t3",
                    "authors": "Alice Zhang et.al.",
                    "arxiv_id": "2401.00003",
                    "pdf_url": "https://arxiv.org/abs/2401.00003",
                    "translate_url": "https://papers.cool/arxiv/2401.00003",
                    "read_url": "https://hjfy.top/arxiv/2401.00003",
                    "code_url": "https://github.com/c/d",
                }
            },
        }

    def test_parse_first_author(self):
        self.assertEqual(parse_first_author("Alice Zhang et.al."), "Alice Zhang")
        self.assertEqual(parse_first_author("Alice Zhang et al."), "Alice Zhang")
        self.assertEqual(parse_first_author("Alice Zhang"), "Alice Zhang")

    def test_daily_counts(self):
        rows = aggregate_daily_counts(self.store)
        # 2026-03-01 LLM count=2
        self.assertIn({"topic": "LLM", "date": "2026-03-01", "count": 2}, rows)

    def test_monthly_counts(self):
        rows = aggregate_monthly_counts(self.store)
        self.assertIn({"topic": "LLM", "date": "2026-03", "count": 2}, rows)
        self.assertIn({"topic": "Multimodal", "date": "2026-03", "count": 1}, rows)

    def test_code_coverage_daily(self):
        rows = aggregate_code_coverage_daily(self.store)
        self.assertIn(
            {
                "topic": "LLM",
                "date": "2026-03-01",
                "total": 2,
                "code_covered": 1,
                "code_coverage": 0.5,
            },
            rows,
        )

    def test_top_first_authors(self):
        top = aggregate_top_first_authors(self.store, start_date="2026-03-01", end_date="2026-03-02", top_n=3)
        # Alice: 2 papers
        self.assertEqual(top[0]["author"], "Alice Zhang")
        self.assertEqual(top[0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行测试确认失败（尚未实现聚合函数）**

Run:
```bash
python -m unittest -v
```

Expected: FAIL（`ModuleNotFoundError: No module named 'utils.analytics'` 或函数不存在）

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/test_analytics.py
git commit -m "test: add analytics aggregation tests"
```

---

### Task 2: 实现聚合核心（counts / coverage / top authors）

**Files:**
- Create: `utils/analytics/__init__.py`
- Create: `utils/analytics/aggregate.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: 创建 utils/analytics/__init__.py**

```python
# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from .aggregate import (
    aggregate_daily_counts,
    aggregate_monthly_counts,
    aggregate_code_coverage_daily,
    aggregate_code_coverage_monthly,
    aggregate_topic_rank,
    aggregate_top_first_authors,
    parse_first_author,
)
```

- [ ] **Step 2: 实现 utils/analytics/aggregate.py（最小实现让测试通过）**

```python
# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

import datetime as _dt
from collections import Counter, defaultdict
from typing import Any


def _iter_records(store: dict[str, dict[str, Any]]):
    for topic, papers in (store or {}).items():
        for paper_id, record in (papers or {}).items():
            if not isinstance(record, dict):
                continue
            date = str(record.get("date", "")).strip()
            if not date:
                continue
            yield topic, paper_id, record


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
    counts = Counter()
    for topic, _, record in _iter_records(store):
        day = str(record["date"])
        counts[(topic, day)] += 1
    rows = [{"topic": t, "date": d, "count": c} for (t, d), c in counts.items()]
    rows.sort(key=lambda r: (r["topic"], r["date"]))
    return rows


def aggregate_monthly_counts(store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter()
    for topic, _, record in _iter_records(store):
        month = _month_of(record["date"])
        counts[(topic, month)] += 1
    rows = [{"topic": t, "date": m, "count": c} for (t, m), c in counts.items()]
    rows.sort(key=lambda r: (r["topic"], r["date"]))
    return rows


def aggregate_code_coverage_daily(store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    totals = Counter()
    covered = Counter()
    for topic, _, record in _iter_records(store):
        day = str(record["date"])
        totals[(topic, day)] += 1
        if record.get("code_url"):
            covered[(topic, day)] += 1
    rows = []
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
    totals = Counter()
    covered = Counter()
    for topic, _, record in _iter_records(store):
        month = _month_of(record["date"])
        totals[(topic, month)] += 1
        if record.get("code_url"):
            covered[(topic, month)] += 1
    rows = []
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
    d = _dt.date.fromisoformat(date_str)
    if start_date:
        if d < _dt.date.fromisoformat(start_date):
            return False
    if end_date:
        if d > _dt.date.fromisoformat(end_date):
            return False
    return True


def aggregate_top_first_authors(
    store: dict[str, dict[str, Any]],
    start_date: str,
    end_date: str,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    counter = Counter()
    for _, _, record in _iter_records(store):
        if not _in_range(record["date"], start_date, end_date):
            continue
        author = parse_first_author(record.get("authors", ""))
        if author:
            counter[author] += 1
    rows = [{"author": a, "count": int(c), "rank": i + 1} for i, (a, c) in enumerate(counter.most_common(top_n))]
    return rows


def aggregate_topic_rank(
    store: dict[str, dict[str, Any]],
    start_date: str,
    end_date: str,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    counter = Counter()
    for topic, _, record in _iter_records(store):
        if not _in_range(record["date"], start_date, end_date):
            continue
        counter[topic] += 1
    rows = [{"topic": t, "count": int(c), "rank": i + 1} for i, (t, c) in enumerate(counter.most_common(top_n))]
    return rows
```

- [ ] **Step 3: 运行测试确认通过**

Run:
```bash
python -m unittest -v
```

Expected: PASS（`tests/test_analytics.py` 全部通过）

- [ ] **Step 4: Commit**

```bash
git add utils/analytics/__init__.py utils/analytics/aggregate.py
git commit -m "feat: add analytics aggregation core"
```

---

### Task 3: 实现导出层（JSON/CSV + meta.json）

**Files:**
- Create: `utils/analytics/export.py`
- Modify: `tests/test_analytics.py`（补充 export 测试）

- [ ] **Step 1: 给 tests 增加 export 的最小回归用例（先失败）**

在 `tests/test_analytics.py` 末尾追加一个测试（保持 unittest 风格）：

```python
import json
import tempfile
from pathlib import Path

from utils.analytics.export import write_json_rows, write_csv_rows, write_meta


class TestAnalyticsExport(unittest.TestCase):
    def test_write_json_and_csv(self):
        rows = [{"topic": "LLM", "date": "2026-03-01", "count": 2}]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            write_json_rows(out / "a.json", rows)
            write_csv_rows(out / "a.csv", rows, fieldnames=["topic", "date", "count"])
            self.assertTrue((out / "a.json").exists())
            self.assertTrue((out / "a.csv").exists())
            data = json.loads((out / "a.json").read_text())
            self.assertEqual(data, rows)

    def test_write_meta(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            write_meta(
                out / "meta.json",
                topics=["LLM", "Multimodal"],
                min_date="2026-03-01",
                max_date="2026-03-02",
                default_range_days=90,
                default_range_months=12,
            )
            meta = json.loads((out / "meta.json").read_text())
            self.assertIn("generated_at", meta)
            self.assertEqual(meta["topics"], ["LLM", "Multimodal"])
```

- [ ] **Step 2: 实现 utils/analytics/export.py**

```python
# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2))


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
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
```

- [ ] **Step 3: 运行测试确认通过**

Run:
```bash
python -m unittest -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add utils/analytics/export.py tests/test_analytics.py
git commit -m "feat: add analytics export helpers"
```

---

### Task 4: 生成静态图（matplotlib）

**Files:**
- Create: `utils/analytics/charts.py`
- Modify: `tests/test_analytics.py`（可选：仅测函数不抛异常）

- [ ] **Step 1: 先加一个最小“能跑”的图表测试（避免 CI 无显示问题）**

在 `tests/test_analytics.py` 里新增：

```python
from utils.analytics.charts import render_trend_chart


class TestAnalyticsCharts(unittest.TestCase):
    def test_render_trend_chart_smoke(self):
        rows = [
            {"topic": "LLM", "date": "2026-03-01", "count": 2},
            {"topic": "LLM", "date": "2026-03-02", "count": 1},
        ]
        # 只验证不抛异常（图像保存到临时目录）
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "trend.png"
            render_trend_chart(rows, out, title="Trend", max_topics=5)
            self.assertTrue(out.exists())
```

- [ ] **Step 2: 实现 utils/analytics/charts.py**

```python
# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def render_trend_chart(rows: list[dict[str, Any]], out_path: Path, title: str, max_topics: int = 10) -> None:
    """
    rows: [{"topic": str, "date": str, "count": int}, ...]
    输出：多折线趋势图（TopN topic）
    """
    import matplotlib
    matplotlib.use("Agg")  # headless
    import matplotlib.pyplot as plt

    # 聚合到 topic -> [(date, count)]
    series = defaultdict(list)
    total_by_topic = defaultdict(int)
    for r in rows:
        t = r["topic"]
        d = r["date"]
        c = int(r.get("count") or 0)
        series[t].append((d, c))
        total_by_topic[t] += c

    top_topics = sorted(total_by_topic.items(), key=lambda kv: kv[1], reverse=True)[:max_topics]
    topics = [t for t, _ in top_topics]
    for t in topics:
        series[t].sort(key=lambda x: x[0])

    _ensure_parent(out_path)
    plt.figure(figsize=(12, 5))
    for t in topics:
        xs = [d for d, _ in series[t]]
        ys = [c for _, c in series[t]]
        plt.plot(xs, ys, linewidth=1.8, label=t)
    plt.title(title)
    plt.xlabel("date")
    plt.ylabel("count")
    plt.xticks(rotation=45, ha="right")
    plt.legend(loc="upper left", fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def render_bar_rank(rows: list[dict[str, Any]], out_path: Path, title: str, x_key: str, y_key: str, top_n: int = 20) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = list(rows)[:top_n]
    labels = [str(r[x_key]) for r in rows][::-1]
    values = [float(r[y_key]) for r in rows][::-1]

    _ensure_parent(out_path)
    plt.figure(figsize=(10, 7))
    plt.barh(labels, values)
    plt.title(title)
    plt.xlabel(y_key)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
```

- [ ] **Step 3: 运行测试确认通过**

Run:
```bash
python -m unittest -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add utils/analytics/charts.py tests/test_analytics.py
git commit -m "feat: add analytics static chart rendering"
```

---

### Task 5: analytics 构建脚本（读取 docs/data → 写 data/charts）

**Files:**
- Create: `scripts/build_analytics.py`

- [ ] **Step 1: 创建脚本（CLI 参数与默认值固定）**

创建 `scripts/build_analytics.py`：

```python
# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from utils.storage import load_paper_store
from utils.analytics.aggregate import (
    aggregate_daily_counts,
    aggregate_monthly_counts,
    aggregate_code_coverage_daily,
    aggregate_code_coverage_monthly,
    aggregate_topic_rank,
    aggregate_top_first_authors,
)
from utils.analytics.export import write_csv_rows, write_json_rows, write_meta
from utils.analytics.charts import render_trend_chart, render_bar_rank


def _infer_date_range(store: dict) -> tuple[str, str]:
    min_d = None
    max_d = None
    for topic, papers in store.items():
        for _, record in (papers or {}).items():
            if not isinstance(record, dict):
                continue
            d = record.get("date")
            if not d:
                continue
            try:
                dd = dt.date.fromisoformat(str(d))
            except Exception:
                continue
            min_d = dd if (min_d is None or dd < min_d) else min_d
            max_d = dd if (max_d is None or dd > max_d) else max_d
    if min_d is None or max_d is None:
        today = dt.date.today()
        return today.isoformat(), today.isoformat()
    return min_d.isoformat(), max_d.isoformat()


def _range_last_days(end: str, days: int) -> tuple[str, str]:
    e = dt.date.fromisoformat(end)
    s = e - dt.timedelta(days=days - 1)
    return s.isoformat(), e.isoformat()


def _range_last_months(end: str, months: int) -> tuple[str, str]:
    # 简化：按月近似到 30 天 * months（第一阶段足够；如需严格按月再升级）
    e = dt.date.fromisoformat(end)
    s = e - dt.timedelta(days=30 * months - 1)
    return s.isoformat(), e.isoformat()


def _range_ytd(end: str) -> tuple[str, str]:
    e = dt.date.fromisoformat(end)
    s = dt.date(e.year, 1, 1)
    return s.isoformat(), e.isoformat()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--store", type=str, default="docs/data", help="paper store path (dir or json)")
    p.add_argument("--out", type=str, default="docs/analytics", help="analytics output root")
    p.add_argument("--default_days", type=int, default=90)
    p.add_argument("--default_months", type=int, default=12)
    p.add_argument("--top_n", type=int, default=20)
    args = p.parse_args()

    store = load_paper_store(Path(args.store))
    out_root = Path(args.out)
    out_data = out_root / "data"
    out_charts = out_root / "charts"

    topics = sorted(store.keys())
    min_date, max_date = _infer_date_range(store)

    # meta
    write_meta(out_data / "meta.json", topics=topics, min_date=min_date, max_date=max_date,
               default_range_days=args.default_days, default_range_months=args.default_months)

    # counts & coverage
    daily_counts = aggregate_daily_counts(store)
    monthly_counts = aggregate_monthly_counts(store)
    cov_daily = aggregate_code_coverage_daily(store)
    cov_monthly = aggregate_code_coverage_monthly(store)

    write_json_rows(out_data / "daily_counts.json", daily_counts)
    write_json_rows(out_data / "monthly_counts.json", monthly_counts)
    write_json_rows(out_data / "code_coverage_daily.json", cov_daily)
    write_json_rows(out_data / "code_coverage_monthly.json", cov_monthly)

    write_csv_rows(out_data / "daily_counts.csv", daily_counts, ["topic", "date", "count"])
    write_csv_rows(out_data / "monthly_counts.csv", monthly_counts, ["topic", "date", "count"])
    write_csv_rows(out_data / "code_coverage_daily.csv", cov_daily, ["topic", "date", "total", "code_covered", "code_coverage"])
    write_csv_rows(out_data / "code_coverage_monthly.csv", cov_monthly, ["topic", "date", "total", "code_covered", "code_coverage"])

    # rank windows (fixed)
    windows = {
        "last_30d": _range_last_days(max_date, 30),
        "last_90d": _range_last_days(max_date, 90),
        "last_12m": _range_last_months(max_date, 12),
        "ytd": _range_ytd(max_date),
    }
    for name, (s, e) in windows.items():
        rank = aggregate_topic_rank(store, start_date=s, end_date=e, top_n=args.top_n)
        authors = aggregate_top_first_authors(store, start_date=s, end_date=e, top_n=args.top_n)
        write_json_rows(out_data / f"topic_rank_{name}.json", rank)
        write_json_rows(out_data / f"top_authors_{name}.json", authors)
        write_csv_rows(out_data / f"topic_rank_{name}.csv", rank, ["topic", "count", "rank"])
        write_csv_rows(out_data / f"top_authors_{name}.csv", authors, ["author", "count", "rank"])

    # charts: choose a default window for static images
    render_trend_chart(daily_counts, out_charts / "trend_daily.png", title="Daily Paper Trend (Top Topics)", max_topics=10)
    render_trend_chart(monthly_counts, out_charts / "trend_monthly.png", title="Monthly Paper Trend (Top Topics)", max_topics=10)
    render_bar_rank(
        aggregate_topic_rank(store, *windows["last_90d"], top_n=20),
        out_charts / "topic_rank.png",
        title="Top Topics (Last 90 Days)",
        x_key="topic",
        y_key="count",
        top_n=20,
    )
    render_bar_rank(
        aggregate_top_first_authors(store, *windows["last_90d"], top_n=20),
        out_charts / "top_authors.png",
        title="Top First Authors (Last 90 Days)",
        x_key="author",
        y_key="count",
        top_n=20,
    )

    # coverage trend: reuse bar rendering on the latest month (simple & stable)
    # For first milestone, keep as rank bar; can be upgraded to line chart later.
    latest_month = max_date[:7]
    latest_cov = [r for r in cov_monthly if r["date"] == latest_month and r["code_coverage"] is not None]
    latest_cov.sort(key=lambda r: r["code_coverage"], reverse=True)
    render_bar_rank(
        [{"topic": r["topic"], "code_coverage": r["code_coverage"]} for r in latest_cov],
        out_charts / "code_coverage_trend.png",
        title=f"Code Coverage by Topic ({latest_month})",
        x_key="topic",
        y_key="code_coverage",
        top_n=20,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 本地运行脚本验证产物生成**

Run:
```bash
python scripts/build_analytics.py --store docs/data --out docs/analytics
```

Expected:
- `docs/analytics/data/meta.json` 存在
- `docs/analytics/charts/trend_daily.png` 等图片存在

- [ ] **Step 3: Commit**

```bash
git add scripts/build_analytics.py utils/analytics
git commit -m "feat: add analytics build script"
```

---

### Task 6: 交互页（docs/analytics/）+ vendored Chart.js

**Files:**
- Create: `docs/analytics/index.html`
- Create: `docs/analytics/assets/app.css`
- Create: `docs/analytics/assets/app.js`
- Create: `docs/analytics/assets/vendor/chart.umd.min.js`

- [ ] **Step 1: vendor Chart.js（固定版本并提交到仓库）**

Run:
```bash
mkdir -p docs/analytics/assets/vendor
curl -L "https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js" -o "docs/analytics/assets/vendor/chart.umd.min.js"
```

Expected:
- 文件存在且非空：`docs/analytics/assets/vendor/chart.umd.min.js`

- [ ] **Step 2: 创建基础页面 docs/analytics/index.html**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Paper List Analytics</title>
    <link rel="stylesheet" href="./assets/app.css" />
  </head>
  <body>
    <header class="header">
      <div class="title">
        <h1>Paper List Analytics</h1>
        <p class="subtitle">离线聚合数据 · 日/月趋势 · Topic 排行 · Code 覆盖率 · Top 第一作者</p>
      </div>
      <div class="meta" id="meta"></div>
    </header>

    <section class="controls">
      <label>
        粒度：
        <select id="granularity">
          <option value="day">日</option>
          <option value="month">月</option>
        </select>
      </label>

      <label>
        时间窗：
        <select id="presetRange">
          <option value="last_30d">最近30天</option>
          <option value="last_90d" selected>最近90天</option>
          <option value="last_12m">最近12个月</option>
          <option value="ytd">今年以来</option>
        </select>
      </label>

      <label>
        Topics（多选）：
        <select id="topics" multiple size="6"></select>
      </label>

      <button id="apply">应用</button>
    </section>

    <main class="grid">
      <section class="card">
        <h2>趋势（Counts）</h2>
        <canvas id="trendChart"></canvas>
      </section>

      <section class="card">
        <h2>Topic 排行</h2>
        <canvas id="rankChart"></canvas>
      </section>

      <section class="card">
        <h2>Code 覆盖率（趋势/近似）</h2>
        <canvas id="coverageChart"></canvas>
      </section>

      <section class="card">
        <h2>Top 第一作者</h2>
        <canvas id="authorsChart"></canvas>
      </section>
    </main>

    <footer class="footer">
      <a href="../index.html">返回 Docs 首页</a>
      <span>·</span>
      <a href="../paper_list.md">paper_list</a>
    </footer>

    <script src="./assets/vendor/chart.umd.min.js"></script>
    <script src="./assets/app.js"></script>
  </body>
</html>
```

- [ ] **Step 3: 创建样式 docs/analytics/assets/app.css**

```css
body {
  margin: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "PingFang SC", "Hiragino Sans GB",
    "Microsoft YaHei", sans-serif;
  background: #0f1115;
  color: #e9edf1;
}

.header {
  padding: 20px 18px;
  border-bottom: 1px solid #262a33;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  align-items: flex-end;
}

.subtitle {
  margin: 6px 0 0;
  color: #aab3bf;
  font-size: 14px;
}

.meta {
  color: #aab3bf;
  font-size: 12px;
  text-align: right;
}

.controls {
  padding: 12px 18px;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  border-bottom: 1px solid #262a33;
}

.controls label {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #c7cfda;
}

select {
  background: #151824;
  color: #e9edf1;
  border: 1px solid #2b3140;
  border-radius: 8px;
  padding: 6px 8px;
}

button {
  background: #2b6cff;
  border: 0;
  color: white;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
}

button:hover {
  background: #245ee0;
}

.grid {
  padding: 18px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

@media (min-width: 1100px) {
  .grid {
    grid-template-columns: 1fr 1fr;
  }
}

.card {
  background: #121520;
  border: 1px solid #262a33;
  border-radius: 14px;
  padding: 12px 12px 16px;
}

.card h2 {
  margin: 6px 6px 10px;
  font-size: 16px;
  color: #dfe6ee;
}

.footer {
  padding: 18px;
  color: #aab3bf;
}

.footer a {
  color: #aab3bf;
}
```

- [ ] **Step 4: 创建交互逻辑 docs/analytics/assets/app.js**

```js
async function fetchJson(path) {
  const r = await fetch(path, { cache: "no-store" })
  if (!r.ok) throw new Error(`Fetch failed: ${path} ${r.status}`)
  return r.json()
}

function uniqSorted(arr) {
  return Array.from(new Set(arr)).sort()
}

function getSelectedOptions(selectEl) {
  return Array.from(selectEl.selectedOptions).map((o) => o.value)
}

function destroyIfExists(chart) {
  if (chart) chart.destroy()
  return null
}

function buildLineDatasets(rows, topics, dateKey, valueKey) {
  // rows: [{topic,date,count}]
  const byTopic = new Map()
  for (const t of topics) byTopic.set(t, new Map())
  for (const r of rows) {
    if (!topics.includes(r.topic)) continue
    byTopic.get(r.topic).set(r[dateKey], r[valueKey])
  }

  const allDates = uniqSorted(rows.map((r) => r[dateKey]))
  const colors = [
    "#2b6cff",
    "#20c997",
    "#ff6b6b",
    "#ffd43b",
    "#845ef7",
    "#74c0fc",
    "#ff922b",
    "#69db7c",
    "#e599f7",
    "#ced4da",
  ]

  const datasets = topics.map((t, idx) => {
    const m = byTopic.get(t) || new Map()
    return {
      label: t,
      data: allDates.map((d) => m.get(d) ?? 0),
      borderColor: colors[idx % colors.length],
      backgroundColor: "transparent",
      tension: 0.2,
      borderWidth: 2,
      pointRadius: 0,
    }
  })
  return { labels: allDates, datasets }
}

function buildBarDataset(rows, labelKey, valueKey, title) {
  const labels = rows.map((r) => r[labelKey])
  const data = rows.map((r) => r[valueKey])
  return {
    labels,
    datasets: [
      {
        label: title,
        data,
        backgroundColor: "#2b6cff",
      },
    ],
  }
}

async function main() {
  const meta = await fetchJson("./data/meta.json")
  document.getElementById("meta").textContent = `数据范围：${meta.min_date} ~ ${meta.max_date} · 生成时间：${meta.generated_at}`

  const topicsEl = document.getElementById("topics")
  for (const t of meta.topics) {
    const opt = document.createElement("option")
    opt.value = t
    opt.textContent = t
    opt.selected = true
    topicsEl.appendChild(opt)
  }

  let trendChart = null
  let rankChart = null
  let coverageChart = null
  let authorsChart = null

  async function render() {
    const granularity = document.getElementById("granularity").value
    const preset = document.getElementById("presetRange").value
    const selectedTopics = getSelectedOptions(topicsEl)
    const topicsForChart = selectedTopics.slice(0, 10) // 控制可读性

    const countsPath = granularity === "day" ? "./data/daily_counts.json" : "./data/monthly_counts.json"
    const covPath = granularity === "day" ? "./data/code_coverage_daily.json" : "./data/code_coverage_monthly.json"

    const [countsRows, covRows, rankRows, authorRows] = await Promise.all([
      fetchJson(countsPath),
      fetchJson(covPath),
      fetchJson(`./data/topic_rank_${preset}.json`),
      fetchJson(`./data/top_authors_${preset}.json`),
    ])

    // trend (counts)
    trendChart = destroyIfExists(trendChart)
    const trendData = buildLineDatasets(countsRows, topicsForChart, "date", "count")
    trendChart = new Chart(document.getElementById("trendChart"), {
      type: "line",
      data: trendData,
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#c7cfda" } } },
        scales: {
          x: { ticks: { color: "#aab3bf", maxRotation: 0 }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    })

    // rank
    rankChart = destroyIfExists(rankChart)
    const topRank = rankRows.slice(0, 20)
    rankChart = new Chart(document.getElementById("rankChart"), {
      type: "bar",
      data: buildBarDataset(topRank, "topic", "count", "Top Topics"),
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    })

    // coverage (render as line by topic: code_coverage)
    coverageChart = destroyIfExists(coverageChart)
    const covTopics = topicsForChart
    const covData = buildLineDatasets(covRows, covTopics, "date", "code_coverage")
    coverageChart = new Chart(document.getElementById("coverageChart"), {
      type: "line",
      data: covData,
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#c7cfda" } } },
        scales: {
          x: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" }, suggestedMin: 0, suggestedMax: 1 },
        },
      },
    })

    // authors
    authorsChart = destroyIfExists(authorsChart)
    const topAuthors = authorRows.slice(0, 20)
    authorsChart = new Chart(document.getElementById("authorsChart"), {
      type: "bar",
      data: buildBarDataset(topAuthors, "author", "count", "Top First Authors"),
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#aab3bf" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    })
  }

  document.getElementById("apply").addEventListener("click", () => {
    render().catch((e) => alert(e.message))
  })

  await render()
}

main().catch((e) => {
  console.error(e)
  alert(e.message)
})
```

- [ ] **Step 5: 本地生成 analytics 数据后，用简单静态服务验证页面可加载**

Run:
```bash
python scripts/build_analytics.py --store docs/data --out docs/analytics
python -m http.server 8000
```

Open:
- `http://localhost:8000/docs/analytics/`

Expected:
- 四张图表能渲染；选择粒度/时间窗后点击“应用”能更新

- [ ] **Step 6: Commit**

```bash
git add docs/analytics/index.html docs/analytics/assets
git commit -m "feat: add analytics dashboard page"
```

---

### Task 7: 为 README / docs/index 注入 Analytics 入口与静态图（避免被生成覆盖）

**Files:**
- Modify: `utils/json_tools.py`

- [ ] **Step 1: 修改 json_to_md 在“Online documentation”之后插入 Analytics 区块**

在 `utils/json_tools.py` 的 `json_to_md()` 中，找到写入：
```python
f.write("Online documentation: [https://islinxu.github.io/paper-list/](https://islinxu.github.io/paper-list/)\\n\\n")
```

紧接其后插入（注意根据 `to_web` 区分相对路径）：

```python
        # Add Analytics入口（静态图 + 交互页）
        if to_web:
            analytics_href = "analytics/"
            charts_prefix = "analytics/charts/"
        else:
            analytics_href = "docs/analytics/"
            charts_prefix = "docs/analytics/charts/"

        f.write("## Analytics\\n\\n")
        f.write(f"- Dashboard: [{analytics_href}]({analytics_href})\\n")
        f.write("\\n")
        f.write(f"![trend_daily]({charts_prefix}trend_daily.png)\\n\\n")
        f.write(f"![topic_rank]({charts_prefix}topic_rank.png)\\n\\n")
        f.write(f"![code_coverage]({charts_prefix}code_coverage_trend.png)\\n\\n")
        f.write(f"![top_authors]({charts_prefix}top_authors.png)\\n\\n")
```

- [ ] **Step 2: 本地运行一次 get_paper / 或直接运行 json_to_md，确认 README 与 docs/index 有 Analytics 区块**

Run（最小化验证：直接渲染 markdown，无需重新抓取）：
```bash
python -c "from utils.json_tools import json_to_md; json_to_md('docs/data','README.md',to_web=False,split_to_docs=True); json_to_md('docs/data','docs/index.md',to_web=True,split_to_docs=True)"
```

Expected:
- `README.md` 与 `docs/index.md` 中出现 “## Analytics” 与图片引用

- [ ] **Step 3: Commit**

```bash
git add utils/json_tools.py README.md docs/index.md
git commit -m "docs: add analytics section to generated markdown"
```

---

### Task 8: 更新 GitHub Actions 工作流（生成 analytics + 提交产物）

**Files:**
- Modify: `.github/workflows/paper-list.yml`
- Modify: `.github/workflows/update_paper_links.yml`

- [ ] **Step 1: 在 paper-list.yml 中 get_paper 后增加 analytics 构建**

在 `Run daily arxiv` 与 `Enrich paper links` 后、提交前，加入：

```yaml
      - name: Build analytics
        run: |
          python scripts/build_analytics.py --store docs/data --out docs/analytics
```

- [ ] **Step 2: 修改 git add 覆盖 docs/analytics 目录**

将：
```yaml
git add README.md docs/*.json docs/*.md docs/wechat.md
```

替换为：
```yaml
git add README.md docs/*.json docs/*.md docs/wechat.md docs/analytics docs/analytics/** || true
```

（说明：`docs/analytics/**` 让新文件确保被加入；`|| true` 避免 glob 在某些 shell 情况下失败。）

- [ ] **Step 3: 在 update_paper_links.yml 中也加入 Build analytics + 扩展 git add**

同样添加：
```yaml
      - name: Build analytics
        run: |
          python scripts/build_analytics.py --store docs/data --out docs/analytics
```

并更新 git add 行与 paper-list.yml 一致。

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/paper-list.yml .github/workflows/update_paper_links.yml
git commit -m "ci: build and commit analytics artifacts"
```

---

### Task 9: 端到端 本地验证（生成 → 页面 → 链接）

**Files:**
- (No new files; validate only)

- [ ] **Step 1: 安装依赖**

Run:
```bash
pip install -r requirements.txt
```

- [ ] **Step 2: 生成 analytics**

Run:
```bash
python scripts/build_analytics.py --store docs/data --out docs/analytics
```

- [ ] **Step 3: 启动本地静态服务检查 docs/index + analytics 页面**

Run:
```bash
python -m http.server 8000
```

Check:
- `http://localhost:8000/docs/index.html`：Analytics 区块与图片加载
- `http://localhost:8000/docs/analytics/`：四张交互图表正常展示

- [ ] **Step 4: Commit（如有生成文件变化）**

```bash
git add docs/analytics README.md docs/index.md
git commit -m "docs: update analytics outputs"
```

---

## Plan self-review

- 覆盖 spec 要求：导出（JSON/CSV）✅、静态图（PNG）✅、交互页（Dashboard）✅、日/月粒度✅、Topic 新增自动适配✅、code_url 覆盖率✅、Top 第一作者✅、CI 集成✅
- 无占位符：所有步骤包含明确文件路径/代码/命令✅
- 命名一致性：`docs/analytics/{data,charts,assets}`、`scripts/build_analytics.py`、`utils/analytics/*` ✅

