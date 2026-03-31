# Generated: 2026-03-31T00:00Z
# Rules-Ver: 3.0.2
# Context-ID: ANALYTICS-001

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.analytics.aggregate import (  # noqa: E402
    aggregate_code_coverage_daily,
    aggregate_code_coverage_monthly,
    aggregate_daily_counts,
    aggregate_monthly_counts,
    aggregate_topic_rank,
    aggregate_top_first_authors,
)
from utils.analytics.charts import render_bar_rank, render_trend_chart  # noqa: E402
from utils.analytics.export import write_csv_rows, write_json_rows, write_meta  # noqa: E402
from utils.storage import load_paper_store  # noqa: E402


def _infer_date_range(store: dict) -> tuple[str, str]:
    min_d: dt.date | None = None
    max_d: dt.date | None = None

    for _, papers in (store or {}).items():
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
    s = e - dt.timedelta(days=int(days) - 1)
    return s.isoformat(), e.isoformat()


def _range_last_months(end: str, months: int) -> tuple[str, str]:
    # 第一阶段：按月窗口用 30 天/月近似即可；如需严格按月边界再升级。
    e = dt.date.fromisoformat(end)
    s = e - dt.timedelta(days=30 * int(months) - 1)
    return s.isoformat(), e.isoformat()


def _range_ytd(end: str) -> tuple[str, str]:
    e = dt.date.fromisoformat(end)
    s = dt.date(e.year, 1, 1)
    return s.isoformat(), e.isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Build analytics datasets and static charts from paper store.")
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

    topics = sorted((store or {}).keys())
    min_date, max_date = _infer_date_range(store)

    # meta
    write_meta(
        out_data / "meta.json",
        topics=topics,
        min_date=min_date,
        max_date=max_date,
        default_range_days=args.default_days,
        default_range_months=args.default_months,
    )

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
    write_csv_rows(
        out_data / "code_coverage_daily.csv",
        cov_daily,
        ["topic", "date", "total", "code_covered", "code_coverage"],
    )
    write_csv_rows(
        out_data / "code_coverage_monthly.csv",
        cov_monthly,
        ["topic", "date", "total", "code_covered", "code_coverage"],
    )

    # rank windows (fixed)
    windows: dict[str, tuple[str, str]] = {
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
    render_trend_chart(
        daily_counts,
        out_charts / "trend_daily.png",
        title="Daily Paper Trend (Top Topics)",
        max_topics=10,
    )
    render_trend_chart(
        monthly_counts,
        out_charts / "trend_monthly.png",
        title="Monthly Paper Trend (Top Topics)",
        max_topics=10,
    )
    render_bar_rank(
        aggregate_topic_rank(store, start_date=windows["last_90d"][0], end_date=windows["last_90d"][1], top_n=20),
        out_charts / "topic_rank.png",
        title="Top Topics (Last 90 Days)",
        x_key="topic",
        y_key="count",
        top_n=20,
    )
    render_bar_rank(
        aggregate_top_first_authors(store, start_date=windows["last_90d"][0], end_date=windows["last_90d"][1], top_n=20),
        out_charts / "top_authors.png",
        title="Top First Authors (Last 90 Days)",
        x_key="author",
        y_key="count",
        top_n=20,
    )

    # coverage trend: reuse bar rendering on the latest month (simple & stable)
    latest_month = str(max_date)[:7]
    latest_cov = [
        r
        for r in (cov_monthly or [])
        if isinstance(r, dict) and r.get("date") == latest_month and r.get("code_coverage") is not None
    ]
    latest_cov.sort(key=lambda r: float(r.get("code_coverage") or 0.0), reverse=True)
    render_bar_rank(
        [{"topic": r.get("topic"), "code_coverage": r.get("code_coverage")} for r in latest_cov],
        out_charts / "code_coverage_trend.png",
        title=f"Code Coverage by Topic ({latest_month})",
        x_key="topic",
        y_key="code_coverage",
        top_n=20,
    )

    print(f"[analytics] store={args.store} topics={len(topics)} date_range={min_date}..{max_date}")
    print(f"[analytics] wrote data to: {out_data}")
    print(f"[analytics] wrote charts to: {out_charts}")


if __name__ == "__main__":
    main()

