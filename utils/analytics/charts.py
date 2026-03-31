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
    Render multi-line trend chart for top topics and save to PNG.

    rows: [{"topic": str, "date": str, "count": int}, ...]
    out_path: output image path (e.g. *.png)
    """

    import matplotlib

    matplotlib.use("Agg")  # headless rendering
    import matplotlib.pyplot as plt

    # topic -> [(date, count)]
    series: dict[str, list[tuple[str, int]]] = defaultdict(list)
    total_by_topic: dict[str, int] = defaultdict(int)

    for r in rows or []:
        if not isinstance(r, dict):
            continue
        topic = str(r.get("topic", "")).strip()
        date = str(r.get("date", "")).strip()
        if not topic or not date:
            continue
        count = int(r.get("count") or 0)
        series[topic].append((date, count))
        total_by_topic[topic] += count

    top_topics = sorted(total_by_topic.items(), key=lambda kv: kv[1], reverse=True)[: int(max_topics or 0)]
    topics = [t for t, _ in top_topics]

    for t in topics:
        # ISO date string sorts correctly for both YYYY-MM-DD / YYYY-MM
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


def render_bar_rank(
    rows: list[dict[str, Any]],
    out_path: Path,
    title: str,
    x_key: str,
    y_key: str,
    top_n: int = 20,
) -> None:
    """
    Render horizontal bar chart for ranking lists.

    Example rows for topic rank:
      [{"topic": "LLM", "count": 320, "rank": 1}, ...]
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = list(rows or [])[: int(top_n or 0)]
    labels = [str(r.get(x_key, "")) for r in rows][::-1]
    values = [float(r.get(y_key) or 0.0) for r in rows][::-1]

    _ensure_parent(out_path)
    plt.figure(figsize=(10, 7))
    plt.barh(labels, values)
    plt.title(title)
    plt.xlabel(y_key)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()

