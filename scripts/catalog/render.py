"""HTML rendering helpers for catalog pages."""

from .shared import (
    FACET_SPECS,
    bucket_counts,
    count_records_with,
    facet_index_link,
    facet_link,
    group_records_by_field,
    short_domain,
    truncate_authors,
)


def analytics_index_link(page_prefix: str = "") -> str:
    return f"{page_prefix}analytics/"


def review_index_link(page_prefix: str = "") -> str:
    return f"{page_prefix}review/"


def render_pill_group(values: list[str], fallback: str, field: str | None = None, page_prefix: str = "") -> str:
    class_name = "archive-pill-group"
    if field == "tasks":
        class_name += " archive-pill-group--tasks"
    if not values:
        return f"<div class='{class_name}'><span class='pill'>{fallback}</span></div>"

    pills = []
    for value in values:
        if field:
            pills.append(f"<a class='pill' href='{facet_link(field, value, page_prefix)}'>{value}</a>")
        else:
            pills.append(f"<span class='pill'>{value}</span>")
    return f"<div class='{class_name}'>{''.join(pills)}</div>"


def render_action_links(record: dict) -> str:
    actions: list[str] = []
    for label, key in [("Paper", "paper_url"), ("Code", "repo_url"), ("Archive", "archive_page_url")]:
        url = record.get(key)
        if not url:
            continue
        actions.append(f"<a href='{url}'>{label}</a>")
    if not actions:
        return "<span class='archive-link archive-link--muted'>Links pending</span>"
    return "".join(actions)


def render_record_card(record: dict, page_prefix: str = "") -> str:
    title = record.get("title") or "Untitled paper"
    year = record.get("publication_year") or "Unknown"
    venue = record.get("venue") or "Venue pending"
    authors = truncate_authors(record.get("authors") or [])
    frameworks = record.get("frameworks") or []
    methods = record.get("methods") or []
    tasks = record.get("tasks") or []
    datasets = record.get("datasets") or []
    benchmarks = record.get("benchmarks") or []
    architecture = record.get("architecture") or []
    repo_topics = record.get("repo_topics") or []
    confidence = record.get("confidence") or {}
    provenance = record.get("source_provenance") or []
    confidence_bits = []
    if confidence.get("paper_match"):
        confidence_bits.append(f"paper {float(confidence['paper_match']):.2f}")
    if confidence.get("repo_match"):
        confidence_bits.append(f"repo {float(confidence['repo_match']):.2f}")
    confidence_text = " · ".join(confidence_bits) or "confidence pending"
    provenance_markup = "".join(
        "<li>"
        f"<span>{item.get('source', 'source')}</span>"
        f"<a href='{item.get('url', '')}'>{short_domain(item.get('url', '')) or 'link'}</a>"
        "</li>"
        for item in provenance[:4]
        if item.get("url")
    )
    return "\n".join(
        [
            "<article class='archive-record'>",
            "  <div class='archive-record__header'>",
            f"    <div><span class='archive-record__year'>{year}</span><h3>{title}</h3></div>",
            f"    <span class='archive-record__venue'>{venue}</span>",
            "  </div>",
            f"  <p class='archive-record__authors'>{authors}</p>",
            f"  {render_pill_group(tasks[:4], 'Unclassified task', 'tasks', page_prefix)}",
            (
                f"  <div><span class='archive-record__label'>Repository topics</span>{render_pill_group(repo_topics[:6], 'No topics')}</div>"
                if repo_topics
                else ""
            ),
            "  <div class='archive-record__taxonomy'>",
            f"    <div><span class='archive-record__label'>Architecture</span>{render_pill_group(architecture[:4], 'Unknown', 'architecture', page_prefix)}</div>",
            f"    <div><span class='archive-record__label'>Frameworks</span>{render_pill_group(frameworks[:4], 'Unknown', 'frameworks', page_prefix)}</div>",
            f"    <div><span class='archive-record__label'>Methods</span>{render_pill_group(methods[:4], 'Unknown', 'methods', page_prefix)}</div>",
            f"    <div><span class='archive-record__label'>Datasets</span>{render_pill_group(datasets[:4], 'Unknown', 'datasets', page_prefix)}</div>",
            f"    <div><span class='archive-record__label'>Benchmarks</span>{render_pill_group(benchmarks[:4], 'Unknown', 'benchmarks', page_prefix)}</div>",
            "  </div>",
            "  <div class='archive-record__footer'>",
            f"    <div class='archive-record__actions'>{render_action_links(record)}</div>",
            f"    <span class='archive-record__confidence'>{confidence_text}</span>",
            "  </div>",
            (
                "  <ul class='archive-provenance'>"
                f"{provenance_markup}"
                "</ul>"
                if provenance_markup
                else ""
            ),
            "</article>",
        ]
    )


def render_signal_card(title: str, body: str) -> str:
    return "\n".join(
        [
            "<article class='signal-card archive-signal-card'>",
            f"  <span class='signal-card__label'>{title}</span>",
            f"  <p>{body}</p>",
            "</article>",
        ]
    )


def render_theme_card(title: str, modifier: str, description: str, items: list[tuple[str, int]], href: str | None = None) -> str:
    stats = "".join(f"<span>{label} <strong>{count}</strong></span>" for label, count in items)
    if not stats:
        stats = "<span>Awaiting archive seeds <strong>0</strong></span>"
    footer = f"<a class='archive-card-link' href='{href}'>Open atlas</a>" if href else ""
    return "\n".join(
        [
            f"<article class='theme-card {modifier} archive-theme-card'>",
            f"  <span class='theme-card__tag'>{title}</span>",
            f"  <p>{description}</p>",
            f"  <div class='archive-theme-card__stats'>{stats}</div>",
            f"  {footer}" if footer else "",
            "</article>",
        ]
    )


def render_timeline_card(year: str, records: list[dict]) -> str:
    titles = [record.get("title") or "Untitled paper" for record in records[:3]]
    items = "".join(f"<li>{title}</li>" for title in titles)
    return "\n".join(
        [
            "<article class='timeline-card archive-timeline-card'>",
            f"  <span class='timeline-card__year'>{year}</span>",
            f"  <h3>{len(records)} archived records</h3>",
            "  <p>Representative captures currently normalized in this repository.</p>",
            f"  <ul class='archive-mini-list'>{items}</ul>",
            "</article>",
        ]
    )


def render_facet_nav(page_prefix: str) -> str:
    items = "".join(
        f"<a href='{facet_index_link(spec['field'], page_prefix)}'>{spec['label']}</a>"
        for spec in FACET_SPECS
    )
    items += f"<a href='{analytics_index_link(page_prefix)}'>Analytics</a>"
    items += f"<a href='{review_index_link(page_prefix)}'>Review Queue</a>"
    return f"<nav class='archive-subnav' aria-label='Archive facets'>{items}</nav>"


def render_count_list(title: str, items: list[tuple[str, int]], field: str | None = None, page_prefix: str = "") -> str:
    rows = []
    for label, count in items:
        target = facet_link(field, label, page_prefix) if field else ""
        label_markup = f"<a href='{target}'>{label}</a>" if target else label
        rows.append(
            "<li>"
            f"<span>{label_markup}</span>"
            f"<strong>{count}</strong>"
            "</li>"
        )
    if not rows:
        rows.append("<li><span>Awaiting records</span><strong>0</strong></li>")
    return "\n".join(
        [
            "<article class='section-card archive-analytics-card'>",
            f"  <h3>{title}</h3>",
            "  <ul class='archive-count-list'>",
            *rows,
            "  </ul>",
            "</article>",
        ]
    )
