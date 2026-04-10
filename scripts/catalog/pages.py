"""Page builders: main catalog, analytics, review, facet indexes and detail pages."""

import argparse
from pathlib import Path

from utils.pwc_archive import load_json, slugify

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
from .review import (
    review_actions,
    review_candidates,
    review_commands,
    review_priority,
    review_reason_counts,
)
from .shared import (
    FACET_SPECS,
    bucket_counts,
    count_records_with,
    facet_index_link,
    facet_link,
    group_records_by_field,
)
from .sync_dashboard import (
    load_blocked_sync_rows,
    load_sync_summary,
    next_retry_epoch,
    render_blocked_sync_list,
    render_retry_glance,
)


def write_markdown_page(path: Path, title: str, body_lines: list[str]) -> None:
    lines = ["---", "layout: default", f"title: {title}", "---", ""] + body_lines
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_main_catalog(records: list[dict], output: Path) -> None:
    project_root = output.parents[2]
    sync = load_sync_summary(project_root)
    blocked_rows = load_blocked_sync_rows(project_root)
    next_retry = next_retry_epoch(project_root)
    total_records = len(records)
    top_tasks = bucket_counts(records, "tasks")
    top_architecture = bucket_counts(records, "architecture")
    top_frameworks = bucket_counts(records, "frameworks")
    top_datasets = bucket_counts(records, "datasets")
    top_benchmarks = bucket_counts(records, "benchmarks")
    top_review_reasons = review_reason_counts(records)
    review_queue = review_candidates(records)
    high_priority = sum(1 for record, reasons in review_queue if review_priority(record, reasons) == "High")
    review_ready = max(total_records - len(review_queue), 0)

    year_buckets: dict[str, list[dict]] = {}
    for record in records:
        year = str(record.get("publication_year") or "Unknown")
        year_buckets.setdefault(year, []).append(record)

    lines = [
        "<section class='hero hero--editorial hero--compact archive-hero'>",
        "  <div class='hero__grid'>",
        "    <div>",
        "      <span class='eyebrow'>Archive Intelligence</span>",
        "      <h1>PapersWithCode Archive Catalog</h1>",
        "      <p>A research dashboard for replayable PapersWithCode history: track what has been normalized, where code coverage is still thin, which review tasks are urgent, and which topic surfaces are already solid enough to browse like a working atlas.</p>",
        "      <div class='hero__actions'>",
        "        <a class='button button--primary' href='#archive-command-deck'>Open command deck</a>",
        "        <a class='button button--ghost' href='#archive-records'>Browse records</a>",
        "        <a class='button button--ghost' href='review/'>Review queue</a>",
        "      </div>",
        f"      {render_facet_nav('')}",
        "    </div>",
        "    <aside class='hero-panel'>",
        "      <span class='hero-panel__label'>Current footprint</span>",
        f"      <div class='hero-panel__stat'><strong>{total_records}</strong><span>Normalized archive-backed paper records currently checked into the repository.</span></div>",
        "      <div class='hero-panel__rail'>",
        f"        <div class='hero-panel__rail-item'><span>{sync['seed_total']}</span><p>Archive seeds currently queued across local manifests and manual source lists.</p></div>",
        f"        <div class='hero-panel__rail-item'><span>{sync['fetched_success']}</span><p>Seed pages already fetched or cached locally for parsing.</p></div>",
        f"        <div class='hero-panel__rail-item'><span>{sync['rate_limited']}</span><p>Wayback requests currently blocked by 429 rate limits and awaiting retry windows.</p></div>",
        "      </div>",
        "    </aside>",
        "  </div>",
        "</section>",
        "",
        "<section id='archive-command-deck' class='archive-command-grid'>",
        "  <article class='archive-command-card archive-command-card--primary'>",
        "    <span class='archive-command-card__eyebrow'>Command deck</span>",
        "    <h3>Browse the archive like a product, not a dump.</h3>",
        "    <p>Jump into the three operating surfaces that matter most: exploration, diagnosis, and repair.</p>",
        "    <div class='archive-command-card__meta'><span>Atlas browsing</span><span>QA routing</span><span>Analytics</span></div>",
        "  </article>",
        f"  <a class='archive-command-card archive-command-card--link' href='tasks/'><span class='archive-command-card__icon'>01</span><strong>Task Atlas</strong><p>Enter by research intent and scan the strongest task clusters first.</p></a>",
        f"  <a class='archive-command-card archive-command-card--link' href='analytics/'><span class='archive-command-card__icon'>02</span><strong>Coverage Board</strong><p>See where frameworks, datasets, and benchmarks are concentrated or missing.</p></a>",
        f"  <a class='archive-command-card archive-command-card--link' href='review/'><span class='archive-command-card__icon'>03</span><strong>Repair Queue</strong><p>Focus on the records that still need provenance, venue, repo topics, or framework recovery.</p></a>",
        "</section>",
        "",
        "<div class='section-divider'>Operational overview</div>",
        "",
        "<section class='archive-dashboard-grid'>",
        "  <article class='archive-health-card archive-health-card--hero'>",
        "    <span class='archive-health-card__eyebrow'>Queue health</span>",
        f"    <div class='archive-health-card__stat'><strong>{high_priority}</strong><span>high-priority records need immediate repair</span></div>",
        "    <p>The review queue is the fastest way to improve research usability because it surfaces missing venue, dataset, benchmark, framework, and provenance gaps in one place.</p>",
        "    <div class='archive-health-card__actions'>",
        "      <a class='archive-card-link' href='review/'>Open review queue</a>",
        "      <a class='archive-card-link' href='analytics/'>Open analytics</a>",
        "    </div>",
        "  </article>",
        "  <article class='archive-health-card'>",
        "    <span class='archive-health-card__eyebrow'>Sync progress</span>",
        f"    <div class='archive-health-card__stat'><strong>{sync['normalized_files']}</strong><span>normalized paper records have completed the current archive ingest lane</span></div>",
        "    <ul class='archive-health-list'>",
        f"      <li><span>Seeds discovered</span><strong>{sync['seed_total']}</strong></li>",
        f"      <li><span>Fetched or cached</span><strong>{sync['fetched_success']}</strong></li>",
        f"      <li><span>Wayback 429 blocked</span><strong>{sync['rate_limited']}</strong></li>",
        f"      <li><span>Pending queue</span><strong>{sync['pending']}</strong></li>",
        "    </ul>",
        "  </article>",
        "  <article class='archive-health-card'>",
        "    <span class='archive-health-card__eyebrow'>Review pressure</span>",
        f"    <div class='archive-health-card__stat'><strong>{len(review_queue)}</strong><span>flagged records are currently waiting for a manual pass</span></div>",
        f"    <ul class='archive-health-list'>{''.join(f'<li><span>{label}</span><strong>{count}</strong></li>' for label, count in top_review_reasons) or '<li><span>No active issues</span><strong>0</strong></li>'}</ul>",
        "  </article>",
        "</section>",
        "",
        "<div class='section-divider'>Sync blockers</div>",
        "",
        "<section class='card-grid card-grid--two archive-analytics-grid'>",
        render_blocked_sync_list(blocked_rows),
        (
            "<article class='section-card archive-analytics-card'>"
            "<h3>Retry policy</h3>"
            f"{render_retry_glance(sync, blocked_rows, next_retry)}"
            "<ul class='archive-count-list'>"
            f"<li><span>Fetch errors total</span><strong>{sync['fetch_errors']}</strong></li>"
            f"<li><span>Normalized records</span><strong>{sync['normalized_files']}</strong></li>"
            f"<li><span>Fetched or cached</span><strong>{sync['fetched_success']}</strong></li>"
            f"<li><span>Seeds discovered</span><strong>{sync['seed_total']}</strong></li>"
            "</ul>"
            "</article>"
        ),
        "</section>",
        "",
        "<div class='section-divider'>Coverage board</div>",
        "",
        "<section class='card-grid card-grid--two archive-analytics-grid'>",
        render_count_list("Top tasks", top_tasks, "tasks"),
        render_count_list("Architecture hints", top_architecture, "architecture"),
        render_count_list("Framework stack", top_frameworks, "frameworks"),
        render_count_list("Dataset coverage", top_datasets, "datasets"),
        render_count_list("Benchmark watch", top_benchmarks, "benchmarks"),
        render_count_list("Review pressure", top_review_reasons, None),
        "</section>",
        "",
        "<div id='archive-timeline' class='section-divider'>Capture timeline</div>",
        "",
        "<section class='timeline-grid timeline-grid--compact timeline-grid--editorial archive-timeline-grid'>",
    ]

    if year_buckets:
        for year, year_records in sorted(year_buckets.items(), key=lambda item: item[0], reverse=True):
            lines.append(render_timeline_card(year, year_records))
    else:
        lines.append(
            "<article class='timeline-card archive-timeline-card'><span class='timeline-card__year'>Awaiting seeds</span><h3>0 archived records</h3><p>Run the archive pipeline to materialize the first normalized snapshot.</p></article>"
        )

    lines.extend(
        [
            "</section>",
            "",
            "<div id='archive-workflow' class='section-divider'>Archive workflow</div>",
            "",
            "<section class='process-grid archive-process-grid'>",
            "  <article class='process-card'><span class='process-card__step'>01</span><h3>Discover</h3><p>Use Wayback CDX, cached snapshots, and manual seeds to assemble candidate paper, task, method, and dataset pages.</p></article>",
            "  <article class='process-card'><span class='process-card__step'>02</span><h3>Preserve</h3><p>Store archived HTML and manifests under <code>data/pwc_archive/raw</code> so parsing decisions remain replayable.</p></article>",
            "  <article class='process-card'><span class='process-card__step'>03</span><h3>Normalize</h3><p>Parse captures into one paper schema with stable ids, repository pointers, confidence scores, and provenance.</p></article>",
            "  <article class='process-card'><span class='process-card__step'>04</span><h3>Enrich</h3><p>Layer OpenAlex and GitHub signals on top for authors, DOI, languages, stars, frameworks, and better task inference.</p></article>",
            "  <article class='process-card'><span class='process-card__step'>05</span><h3>Review</h3><p>Filter low-signal concepts, inspect provenance, and keep manual URLs for high-value papers that deserve a second pass.</p></article>",
            "  <article class='process-card'><span class='process-card__step'>06</span><h3>Publish</h3><p>Render a browseable research catalog inside GitHub Pages so the archive becomes a durable working notebook.</p></article>",
            "</section>",
            "",
            "<div class='card-grid archive-signal-grid'>",
            render_signal_card("Traceability", "Every normalized entry keeps its archive capture URL and provenance chain so later corrections can always be traced back to raw evidence."),
            render_signal_card("Reproduction readiness", "Code links, language mixes, frameworks, and architecture labels make it easier to decide what is worth cloning and reproducing next."),
            render_signal_card("Catalog strategy", "The repository now supports a split workflow: archive discovery, raw preservation, normalization, enrichment, and finally browseable GitHub Pages output."),
            render_signal_card("Rate-limit hygiene", "GitHub enrichment is much more stable with a personal access token. Set GITHUB_TOKEN before large batches so repository topics, README hints, and language data can be recovered consistently."),
            "</div>",
            "",
            "<div id='archive-records' class='section-divider'>Normalized records</div>",
            "",
            "<section class='archive-record-grid'>",
        ]
    )

    if not records:
        lines.append(
            "<article class='archive-empty-state'><h3>No normalized records yet</h3><p>Run the sample scripts in <code>scripts/</code> to populate the first archive-backed paper cards.</p></article>"
        )
    else:
        for record in records:
            lines.append(render_record_card(record))

    lines.extend(
        [
            "</section>",
            "",
            "<div class='section-divider'>Seed paths</div>",
            "",
            "<section class='card-grid card-grid--two archive-seed-grid'>",
            "  <article class='section-card'><h3>Fast path</h3><p>Use cached local seeds when Wayback is rate-limited: <code>python scripts/pwc_run_pipeline.py --use-local-seeds --limit 5</code>.</p></article>",
            "  <article class='section-card'><h3>Replayability</h3><p>Keep <code>raw</code>, <code>staging</code>, and <code>normalized</code> layers separate so every generated page can be traced back to its origin.</p></article>",
            "  <article class='section-card'><h3>Archive analytics</h3><p>Use <a href='analytics/'>Archive Analytics</a> to inspect the current task, framework, dataset, and benchmark mix.</p></article>",
            "  <article class='section-card'><h3>GitHub token</h3><p>Before running <code>python scripts/pwc_enrich_github.py</code> at scale, export <code>GITHUB_TOKEN</code> to reduce rate limits and recover repository topics, homepage hints, and README-backed metadata more reliably.</p></article>",
            "</section>",
        ]
    )

    write_markdown_page(output, "PapersWithCode Archive Catalog", lines)


def build_analytics_page(records: list[dict], base_dir: Path) -> None:
    lines = [
        "<section class='hero hero--editorial hero--compact archive-hero archive-hero--subpage'>",
        "  <div class='hero__grid'>",
        "    <div>",
        "      <span class='eyebrow'>Archive Analytics</span>",
        "      <h1>PWC Archive Analytics</h1>",
        "      <p>A compact summary of the current normalized archive slice, designed to show which tasks, methods, frameworks, datasets, and benchmarks dominate the catalog.</p>",
        "      <div class='hero__actions'>",
        "        <a class='button button--primary' href='../index.html'>Back to catalog</a>",
        "        <a class='button button--ghost' href='#analytics-breakdown'>Jump to breakdown</a>",
        "      </div>",
        f"      {render_facet_nav('../')}",
        "    </div>",
        "    <aside class='hero-panel'>",
        "      <span class='hero-panel__label'>Snapshot</span>",
        f"      <div class='hero-panel__stat'><strong>{len(records)}</strong><span>Normalized records currently included in this analytics snapshot.</span></div>",
        "      <div class='hero-panel__rail'>",
        f"        <div class='hero-panel__rail-item'><span>{count_records_with(records, 'repo_url')}</span><p>Records with linked code repositories.</p></div>",
        f"        <div class='hero-panel__rail-item'><span>{count_records_with(records, 'datasets')}</span><p>Records already carrying at least one dataset label.</p></div>",
        f"        <div class='hero-panel__rail-item'><span>{count_records_with(records, 'benchmarks')}</span><p>Records already carrying at least one benchmark label.</p></div>",
        "      </div>",
        "    </aside>",
        "  </div>",
        "</section>",
        "",
        "<section class='hero__metrics archive-metric-grid'>",
        f"<article class='metric-card'><strong>{len(group_records_by_field(records, 'tasks'))}</strong><span>distinct tasks</span></article>",
        f"<article class='metric-card'><strong>{len(group_records_by_field(records, 'frameworks'))}</strong><span>distinct frameworks</span></article>",
        f"<article class='metric-card'><strong>{len(group_records_by_field(records, 'datasets'))}</strong><span>distinct datasets</span></article>",
        f"<article class='metric-card'><strong>{len(group_records_by_field(records, 'benchmarks'))}</strong><span>distinct benchmarks</span></article>",
        "</section>",
        "",
        "<div id='analytics-breakdown' class='section-divider'>Breakdown</div>",
        "",
        "<section class='card-grid card-grid--two archive-analytics-grid'>",
        render_count_list("Top tasks", bucket_counts(records, "tasks", limit=8), "tasks", "../"),
        render_count_list("Top methods", bucket_counts(records, "methods", limit=8), "methods", "../"),
        render_count_list("Top frameworks", bucket_counts(records, "frameworks", limit=8), "frameworks", "../"),
        render_count_list("Top datasets", bucket_counts(records, "datasets", limit=8), "datasets", "../"),
        render_count_list("Top benchmarks", bucket_counts(records, "benchmarks", limit=8), "benchmarks", "../"),
        render_count_list("Top architectures", bucket_counts(records, "architecture", limit=8), "architecture", "../"),
        "</section>",
        "",
        "<div class='section-divider'>Coverage notes</div>",
        "",
        "<section class='card-grid card-grid--two archive-seed-grid'>",
        "  <article class='section-card'><h3>Interpret carefully</h3><p>This page reflects only the currently normalized slice, not the full PapersWithCode archive universe.</p></article>",
        "  <article class='section-card'><h3>Best next move</h3><p>Use these counts to decide which tasks or datasets need more seed URLs, more enrichment, or a manual QA pass.</p></article>",
        "</section>",
    ]
    write_markdown_page(base_dir / "analytics/index.md", "PWC Archive Analytics", lines)


def build_review_page(records: list[dict], base_dir: Path) -> None:
    queue = review_candidates(records)
    priority_counts = {
        "High": sum(1 for record, reasons in queue if review_priority(record, reasons) == "High"),
        "Medium": sum(1 for record, reasons in queue if review_priority(record, reasons) == "Medium"),
        "Low": sum(1 for record, reasons in queue if review_priority(record, reasons) == "Low"),
    }
    lines = [
        "<section class='hero hero--editorial hero--compact archive-hero archive-hero--subpage'>",
        "  <div class='hero__grid'>",
        "    <div>",
        "      <span class='eyebrow'>Review Queue</span>",
        "      <h1>PWC QA Review Queue</h1>",
        "      <p>This page surfaces the records that most need human attention: low-confidence matches, missing provenance detail, or missing reproducibility fields such as venue, datasets, benchmarks, and repository topics.</p>",
        "      <div class='hero__actions'>",
        "        <a class='button button--primary' href='../index.html'>Back to catalog</a>",
        "        <a class='button button--ghost' href='#review-records'>Jump to queue</a>",
        "      </div>",
        f"      {render_facet_nav('../')}",
        "    </div>",
        "    <aside class='hero-panel'>",
        "      <span class='hero-panel__label'>Queue size</span>",
        f"      <div class='hero-panel__stat'><strong>{len(queue)}</strong><span>Records currently flagged for a manual pass.</span></div>",
        "      <div class='hero-panel__rail'>",
        f"        <div class='hero-panel__rail-item'><span>{priority_counts['High']}</span><p>High-priority records that likely need immediate metadata repair.</p></div>",
        f"        <div class='hero-panel__rail-item'><span>{priority_counts['Medium']}</span><p>Medium-priority records that still need enrichment or audit work.</p></div>",
        f"        <div class='hero-panel__rail-item'><span>{priority_counts['Low']}</span><p>Low-priority records with lighter cleanup needs.</p></div>",
        "      </div>",
        "    </aside>",
        "  </div>",
        "</section>",
        "",
        "<div class='section-divider'>Review principles</div>",
        "",
        "<section class='card-grid card-grid--two archive-seed-grid'>",
        "  <article class='section-card'><h3>Prioritize evidence gaps</h3><p>Start with records missing venue, datasets, benchmarks, or repository topics, because those fields drive both search quality and reproduction planning.</p></article>",
        "  <article class='section-card'><h3>Preserve provenance</h3><p>When you fix a record, prefer adding new evidence links rather than overwriting fields without a traceable source.</p></article>",
        "</section>",
        "",
        "<section class='hero__metrics archive-metric-grid'>",
        f"<article class='metric-card'><strong>{priority_counts['High']}</strong><span>high priority</span></article>",
        f"<article class='metric-card'><strong>{priority_counts['Medium']}</strong><span>medium priority</span></article>",
        f"<article class='metric-card'><strong>{priority_counts['Low']}</strong><span>low priority</span></article>",
        f"<article class='metric-card'><strong>{len(queue)}</strong><span>total flagged</span></article>",
        "</section>",
        "",
        "<div id='review-records' class='section-divider'>Flagged records</div>",
        "",
        "<section class='archive-review-grid'>",
    ]
    if not queue:
        lines.append("<article class='archive-empty-state'><h3>Queue is clear</h3><p>No records are currently flagged for manual review.</p></article>")
    else:
        for record, reasons in queue:
            actions = review_actions(record, reasons)
            commands = review_commands(record, reasons)
            priority = review_priority(record, reasons)
            lines.extend(
                [
                    f"<article class='archive-review-card archive-review-card--{priority.lower()}'>",
                    f"  <div class='archive-review-card__header'><span class='archive-priority archive-priority--{priority.lower()}'>{priority} priority</span></div>",
                    f"  <div class='archive-review-card__reasons'>{render_pill_group(reasons[:6], 'Needs review')}</div>",
                    (
                        "  <div class='archive-review-card__actions'>"
                        "<span class='archive-record__label'>Suggested next steps</span>"
                        "<ul class='archive-review-actions'>"
                        + "".join(f"<li>{action}</li>" for action in actions)
                        + "</ul></div>"
                        if actions
                        else ""
                    ),
                    (
                        "  <div class='archive-review-card__commands'>"
                        "<span class='archive-record__label'>Suggested commands</span>"
                        "<ul class='archive-review-commands'>"
                        + "".join(f"<li><code>{command}</code></li>" for command in commands)
                        + "</ul></div>"
                        if commands
                        else ""
                    ),
                    f"  {render_record_card(record, '../')}",
                    "</article>",
                ]
            )
    lines.append("</section>")
    write_markdown_page(base_dir / "review/index.md", "PWC QA Review Queue", lines)


def build_facet_index(records: list[dict], base_dir: Path, spec: dict) -> None:
    groups = group_records_by_field(records, spec["field"])
    directory = base_dir / spec["directory"]
    cards = []
    for label, label_records in groups:
        cards.append(
            "\n".join(
                [
                    "<article class='topic-card archive-index-card'>",
                    f"  <span class='topic-card__tag'>{spec['label']}</span>",
                    f"  <h3>{label}</h3>",
                    f"  <p>{len(label_records)} normalized records currently map to this archive facet.</p>",
                    "  <div class='topic-card__meta'>",
                    f"    <span class='pill'>{len(label_records)} records</span>",
                    f"    <a class='topic-card__arrow' href='{slugify(label)}.html' aria-label='Open {label}'>&#8599;</a>",
                    "  </div>",
                    "</article>",
                ]
            )
        )

    lines = [
        "<section class='hero hero--editorial hero--compact archive-hero archive-hero--subpage'>",
        "  <div class='hero__grid'>",
        "    <div>",
        f"      <span class='eyebrow'>{spec['label']} Atlas</span>",
        f"      <h1>{spec['title']}</h1>",
        f"      <p>{spec['description']}</p>",
        "      <div class='hero__actions'>",
        "        <a class='button button--primary' href='../index.html'>Back to catalog</a>",
        "        <a class='button button--ghost' href='#facet-index'>Jump to entries</a>",
        "      </div>",
        f"      {render_facet_nav('../')}",
        "    </div>",
        "    <aside class='hero-panel'>",
        "      <span class='hero-panel__label'>Facet coverage</span>",
        f"      <div class='hero-panel__stat'><strong>{len(groups)}</strong><span>Distinct {spec['label'].lower()} currently discoverable from normalized records.</span></div>",
        f"      <div class='hero-panel__rail'><div class='hero-panel__rail-item'><span>{len(records)}</span><p>Total normalized records available to map into this browsing dimension.</p></div></div>",
        "    </aside>",
        "  </div>",
        "</section>",
        "",
        "<div id='facet-index' class='section-divider'>Facet index</div>",
        "",
        "<section class='topic-grid archive-index-grid'>",
    ]
    if cards:
        lines.extend(cards)
    else:
        lines.append("<article class='archive-empty-state'><h3>No indexed entries yet</h3><p>Run the parser and enrichment flow to populate this browsing dimension.</p></article>")
    lines.append("</section>")
    write_markdown_page(directory / "index.md", spec["title"], lines)


def build_facet_detail_pages(records: list[dict], base_dir: Path, spec: dict) -> None:
    groups = group_records_by_field(records, spec["field"])
    directory = base_dir / spec["directory"]
    for label, label_records in groups:
        lines = [
            "<section class='hero hero--editorial hero--compact archive-hero archive-hero--subpage'>",
            "  <div class='hero__grid'>",
            "    <div>",
            f"      <span class='eyebrow'>{spec['label']} Detail</span>",
            f"      <h1>{label}</h1>",
            f"      <p>{len(label_records)} normalized records currently connect to this {spec['label'].lower()} facet.</p>",
            "      <div class='hero__actions'>",
            "        <a class='button button--primary' href='./'>Back to atlas</a>",
            "        <a class='button button--ghost' href='../index.html'>Catalog home</a>",
            "      </div>",
            f"      {render_facet_nav('../')}",
            "    </div>",
            "    <aside class='hero-panel'>",
            "      <span class='hero-panel__label'>Facet notes</span>",
            f"      <div class='hero-panel__stat'><strong>{len(label_records)}</strong><span>Records aligned to this label across archive parsing and enrichment.</span></div>",
            "      <div class='hero-panel__rail'>",
            f"        <div class='hero-panel__rail-item'><span>{spec['label']}</span><p>Use provenance and linked repositories below to verify whether this tag should stay, split, or be renamed.</p></div>",
            "      </div>",
            "    </aside>",
            "  </div>",
            "</section>",
            "",
            "<div class='section-divider'>Matching records</div>",
            "",
            "<section class='archive-record-grid'>",
        ]
        for record in label_records:
            lines.append(render_record_card(record, "../"))
        lines.append("</section>")
        write_markdown_page(directory / f"{slugify(label)}.md", label, lines)


def build_catalog(input_dir: Path, output: Path) -> list[dict]:
    records = []
    for file_path in sorted(input_dir.glob("*.json")):
        record = load_json(file_path, {})
        if record:
            record["_source_file"] = file_path.as_posix()
            records.append(record)

    records = sorted(
        records,
        key=lambda record: (
            -(record.get("publication_year") or 0),
            str(record.get("title") or "").lower(),
        ),
    )

    base_dir = output.parent
    build_main_catalog(records, output)
    build_analytics_page(records, base_dir)
    build_review_page(records, base_dir)
    for spec in FACET_SPECS:
        build_facet_index(records, base_dir, spec)
        build_facet_detail_pages(records, base_dir, spec)
    return records
