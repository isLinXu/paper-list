"""PapersWithCode Archive Catalog Builder.

Modular catalog generator that turns normalized PWC archive records
into browseable Jekyll/GitHub Pages markdown with facet indexes,
analytics dashboards, review queues, and operational monitoring.
"""

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
from .render import (
    analytics_index_link,
    render_action_links,
    render_count_list,
    render_facet_nav,
    render_pill_group,
    render_record_card,
    render_signal_card,
    render_theme_card,
    render_timeline_card,
    review_index_link,
)
from .sync_dashboard import (
    blocked_entity_counts,
    blocked_error_label,
    infer_error_kind,
    load_blocked_sync_rows,
    load_sync_summary,
    next_retry_epoch,
    render_blocked_sync_list,
    render_retry_glance,
    retry_label,
    retry_schedule_label,
)
from .review import (
    capture_age_days,
    review_actions,
    review_candidates,
    review_commands,
    review_priority,
    review_reason_counts,
    review_reasons,
)
from .pages import (
    build_analytics_page,
    build_catalog,
    build_facet_detail_pages,
    build_facet_index,
    build_main_catalog,
    build_review_page,
    write_markdown_page,
)

__all__ = [
    # shared
    "FACET_SPECS",
    "bucket_counts",
    "count_records_with",
    "facet_index_link",
    "facet_link",
    "group_records_by_field",
    "short_domain",
    "truncate_authors",
    # render
    "analytics_index_link",
    "render_action_links",
    "render_count_list",
    "render_facet_nav",
    "render_pill_group",
    "render_record_card",
    "render_signal_card",
    "render_theme_card",
    "render_timeline_card",
    "review_index_link",
    # sync_dashboard
    "blocked_entity_counts",
    "blocked_error_label",
    "infer_error_kind",
    "load_blocked_sync_rows",
    "load_sync_summary",
    "next_retry_epoch",
    "render_blocked_sync_list",
    "render_retry_glance",
    "retry_label",
    "retry_schedule_label",
    # review
    "capture_age_days",
    "review_actions",
    "review_candidates",
    "review_commands",
    "review_priority",
    "review_reason_counts",
    "review_reasons",
    # pages
    "build_analytics_page",
    "build_catalog",
    "build_facet_detail_pages",
    "build_facet_index",
    "build_main_catalog",
    "build_review_page",
    "write_markdown_page",
]
