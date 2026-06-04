import datetime
import logging

from .markdown_renderer import (
    write_badge_section,
    write_title_header,
    write_introduction_section,
    write_features_section,
    write_workflow_section,
    write_quickstart_section,
    write_paper_table,
    write_monthly_archive,
    write_footer_sections,
)
from .storage import load_paper_store


TOPIC_GROUPS = [
    (
        "Perception Core",
        "Vision Systems",
        "theme-card--vision",
        ["Classification", "Object Detection", "Semantic Segmentation", "Anomaly Detection"],
    ),
    (
        "3D and Motion",
        "Geometry Stack",
        "theme-card--motion",
        ["Object Tracking", "Action Recognition", "Pose Estimation", "Depth Estimation", "Optical Flow"],
    ),
    (
        "Foundation Models",
        "Generative Layer",
        "theme-card--foundation",
        ["Image Generation", "Diffusion Models", "LLM", "Latent Space LLM", "Multimodal"],
    ),
    (
        "Systems Frontier",
        "Research Surface",
        "theme-card--systems",
        [
            "Scene Understanding",
            "Video Understanding",
            "Neural Rendering",
            "Transfer Learning",
            "Reinforcement Learning",
            "Graph Neural Networks",
            "Audio Processing",
        ],
    ),
]


def flatten_topic_groups() -> list[str]:
    ordered = []
    for _, _, _, topics in TOPIC_GROUPS:
        for topic in topics:
            if topic not in ordered:
                ordered.append(topic)
    return ordered


def build_topic_metadata(data: dict) -> dict:
    ordered_topics = [topic for topic in flatten_topic_groups() if data.get(topic)]
    fallback_topics = [topic for topic, papers in data.items() if papers and topic not in ordered_topics]
    full_order = ordered_topics + fallback_topics
    meta = {}

    for index, topic in enumerate(full_order):
        prev_topic = full_order[index - 1] if index > 0 else None
        next_topic = full_order[index + 1] if index + 1 < len(full_order) else None
        lane_title = "Research Track"
        lane_eyebrow = "Topic Lane"
        for eyebrow, title, _, topics in TOPIC_GROUPS:
            if topic in topics:
                lane_title = title
                lane_eyebrow = eyebrow
                break
        meta[topic] = {
            "prev": prev_topic,
            "next": next_topic,
            "lane_title": lane_title,
            "lane_eyebrow": lane_eyebrow,
        }
    return meta


def compute_library_stats(data: dict) -> dict:
    topic_counts = []
    dates = []
    total_papers = 0

    for keyword, papers in data.items():
        if not papers:
            continue
        total_papers += len(papers)
        topic_counts.append((keyword, len(papers)))
        for paper_id, entry in papers.items():
            record = ensure_paper_record(entry, paper_id=paper_id)
            if record.get("date"):
                dates.append(record["date"])

    topic_counts.sort(key=lambda item: (-item[1], item[0]))
    dates.sort()
    return {
        "topic_total": len(topic_counts),
        "paper_total": total_papers,
        "first_date": dates[0] if dates else "",
        "last_date": dates[-1] if dates else "",
        "top_topics": topic_counts[:3],
    }


def topic_href(keyword: str, *, to_web: bool, split_to_docs: bool) -> str:
    slug = keyword.replace(" ", "_")
    if split_to_docs:
        return f"{slug}.md" if to_web else f"docs/{slug}.md"
    return f"#{keyword.replace(' ', '-').lower()}"


def write_topic_index(handle, data: dict, *, to_web: bool, split_to_docs: bool) -> None:
    handle.write("## 📚 Paper List\n\n")
    if split_to_docs:
        handle.write("Browse topics by research lane first, then jump into each monthly archive.\n\n")
    else:
        handle.write("Use the topic index below to jump straight into the full paper tables:\n\n")
    handle.write("<ul class=\"topic-index\">\n")
    topic_num = 1
    seen = set()
    for keyword in flatten_topic_groups():
        day_content = data.get(keyword)
        if not day_content:
            continue
        href = topic_href(keyword, to_web=to_web, split_to_docs=split_to_docs)
        handle.write(
            f"  <li><a href=\"{href}\"><span class=\"topic-index__label\"><span class=\"topic-index__number\">{topic_num}</span><span>{keyword}</span></span></a></li>\n"
        )
        topic_num += 1
        seen.add(keyword)

    for keyword, day_content in data.items():
        if not day_content or keyword in seen:
            continue
        href = topic_href(keyword, to_web=to_web, split_to_docs=split_to_docs)
        handle.write(
            f"  <li><a href=\"{href}\"><span class=\"topic-index__label\"><span class=\"topic-index__number\">{topic_num}</span><span>{keyword}</span></span></a></li>\n"
        )
        topic_num += 1
    handle.write("</ul>\n\n")


def write_home_hero(handle, stats: dict, date_now: str) -> None:
    date_range = f"{stats['first_date']} to {stats['last_date']}" if stats["first_date"] and stats["last_date"] else "Daily refresh window"
    top_topics = ", ".join(topic for topic, _ in stats["top_topics"]) or "Classification, Detection, LLM"

    handle.write("<section class=\"hero hero--editorial\">\n")
    handle.write("  <div class=\"hero__grid\">\n")
    handle.write("    <div>\n")
    handle.write("      <span class=\"eyebrow\">Research Radar</span>\n")
    handle.write("      <h1>Track the latest arXiv papers without losing the map.</h1>\n")
    handle.write("      <p>Paper-List-DAILY turns raw daily paper updates into a cleaner topic-structured research surface: enter through grouped themes, open monthly archives, or fall back to the full feed when you want the dense version.</p>\n")
    handle.write("      <div class=\"hero__actions\">\n")
    handle.write("        <a class=\"button button--primary\" href=\"#topic-lanes\">Browse topic lanes</a>\n")
    handle.write("        <a class=\"button button--ghost\" href=\"paper_list.html\">Open full paper list</a>\n")
    handle.write("        <a class=\"button button--ghost\" href=\"https://github.com/isLinXu/paper-list\">GitHub repo</a>\n")
    handle.write("      </div>\n")
    handle.write("      <div class=\"page-meta\">\n")
    handle.write(f"        <span class=\"pill\">Updated {date_now}</span>\n")
    handle.write(f"        <span class=\"pill\">{stats['topic_total']} tracked topics</span>\n")
    handle.write(f"        <span class=\"pill\">{stats['paper_total']} indexed papers</span>\n")
    handle.write(f"        <span class=\"pill\">{date_range}</span>\n")
    handle.write("      </div>\n")
    handle.write("    </div>\n")
    handle.write("    <aside class=\"hero-panel\">\n")
    handle.write("      <span class=\"hero-panel__label\">Snapshot</span>\n")
    handle.write(f"      <div class=\"hero-panel__stat\"><strong>{stats['paper_total']}</strong><span>papers currently split into monthly archive pages that are easier to browse than one giant feed.</span></div>\n")
    handle.write("      <div class=\"hero-panel__rail\">\n")
    handle.write(f"        <div class=\"hero-panel__rail-item\"><span>{stats['topic_total']}</span><p>research tracks currently covered across vision, multimodal, and learning systems.</p></div>\n")
    handle.write("        <div class=\"hero-panel__rail-item\"><span>Every 8h</span><p>GitHub Actions refresh cadence for data, docs, and analytics artifacts.</p></div>\n")
    handle.write(f"        <div class=\"hero-panel__rail-item\"><span>Top lanes</span><p>{top_topics}</p></div>\n")
    handle.write("      </div>\n")
    handle.write("    </aside>\n")
    handle.write("  </div>\n")
    handle.write("</section>\n\n")

    handle.write("<div class=\"section-divider\"><span>Topic Lanes</span></div>\n\n")
    handle.write("<section id=\"topic-lanes\" class=\"theme-grid theme-grid--compact\">\n")
    for eyebrow, title, card_class, topics in TOPIC_GROUPS:
        links = []
        for topic in topics:
            href = topic_href(topic, to_web=True, split_to_docs=True)
            links.append(f"<a href=\"{href}\">{topic}</a>")
        handle.write(f"  <article class=\"theme-card {card_class}\">\n")
        handle.write(f"    <span class=\"theme-card__tag\">{eyebrow}</span>\n")
        handle.write(f"    <h3>{title}</h3>\n")
        handle.write("    <p>Use this lane when you want a tighter set of related research problems instead of one giant alphabetical directory.</p>\n")
        handle.write(f"    <div class=\"theme-card__links\">{''.join(links)}</div>\n")
        handle.write("  </article>\n")
    handle.write("</section>\n\n")

    handle.write("<section class=\"timeline-grid timeline-grid--compact timeline-grid--editorial\">\n")
    handle.write("  <article class=\"timeline-card\"><span class=\"timeline-card__year\">Step 01</span><h3>Pick a lane</h3><p>Start with grouped research surfaces above when you want fast orientation instead of a long flat directory.</p></article>\n")
    handle.write("  <article class=\"timeline-card\"><span class=\"timeline-card__year\">Step 02</span><h3>Open a topic</h3><p>Each topic page acts like a compact hub with month-level entries, which is better for repeat browsing.</p></article>\n")
    handle.write("  <article class=\"timeline-card\"><span class=\"timeline-card__year\">Step 03</span><h3>Read or scan</h3><p>Use monthly archives for focused reading, or switch to the full feed only when you need the dense raw stream.</p></article>\n")
    handle.write("</section>\n\n")
    handle.write("<div class=\"section-divider\"><span>Topic Directory</span></div>\n\n")

    handle.write("<section class=\"explorer-strip\">\n")
    handle.write("  <article class=\"explorer-card explorer-card--primary\">\n")
    handle.write("    <span class=\"explorer-card__eyebrow\">Main entry</span>\n")
    handle.write("    <h3>Topic-first browsing</h3>\n")
    handle.write("    <p>Best for most visits: open a theme, choose a topic, then browse month by month.</p>\n")
    handle.write("  </article>\n")
    handle.write("  <a class=\"explorer-card explorer-card--link\" href=\"paper_list.html\"><span class=\"explorer-card__icon\">01</span><strong>Full Paper List</strong><p>Open the dense all-topics index when you want one continuous searchable stream.</p></a>\n")
    handle.write("  <a class=\"explorer-card explorer-card--link\" href=\"analytics/\"><span class=\"explorer-card__icon\">02</span><strong>Research Insights</strong><p>Open trend charts and metrics only when you specifically want analytics.</p></a>\n")
    handle.write("</section>\n\n")


def write_catalog_intro(handle, stats: dict, date_now: str) -> None:
    date_range = f"{stats['first_date']} to {stats['last_date']}" if stats["first_date"] and stats["last_date"] else "Daily refresh window"
    handle.write("<section class=\"hero hero--editorial hero--compact\">\n")
    handle.write("  <div class=\"hero__grid\">\n")
    handle.write("    <div>\n")
    handle.write("      <span class=\"eyebrow\">Full Feed</span>\n")
    handle.write("      <h1>All tracked papers in one dense index.</h1>\n")
    handle.write("      <p>This page is the raw scanning surface: topic anchors first, then full paper tables for researchers who prefer one continuous archive over topic landing pages.</p>\n")
    handle.write("      <div class=\"hero__actions\">\n")
    handle.write("        <a class=\"button button--primary\" href=\"#paper-list\">Jump to topics</a>\n")
    handle.write("        <a class=\"button button--ghost\" href=\"index.html\">Back to homepage</a>\n")
    handle.write("        <a class=\"button button--ghost\" href=\"analytics/\">Research insights</a>\n")
    handle.write("      </div>\n")
    handle.write("      <div class=\"page-meta\">\n")
    handle.write(f"        <span class=\"pill\">Updated {date_now}</span>\n")
    handle.write(f"        <span class=\"pill\">{stats['paper_total']} papers</span>\n")
    handle.write(f"        <span class=\"pill\">{date_range}</span>\n")
    handle.write("      </div>\n")
    handle.write("    </div>\n")
    handle.write("    <aside class=\"hero-panel\">\n")
    handle.write("      <span class=\"hero-panel__label\">How to use it</span>\n")
    handle.write("      <div class=\"hero-panel__stat\"><strong>Dense mode</strong><span>Stay on this page when you want to search the whole stream quickly with browser find, then pivot out only when a topic deserves deeper browsing.</span></div>\n")
    handle.write("      <div class=\"hero-panel__rail\">\n")
    handle.write(f"        <div class=\"hero-panel__rail-item\"><span>{stats['topic_total']}</span><p>topic anchors are listed below for quick movement.</p></div>\n")
    handle.write("        <div class=\"hero-panel__rail-item\"><span>PDF + code</span><p>direct action links stay embedded in every row for minimal friction.</p></div>\n")
    handle.write("        <div class=\"hero-panel__rail-item\"><span>Monthly pages</span><p>home topic pages remain the better option when you want smaller, calmer reading chunks.</p></div>\n")
    handle.write("      </div>\n")
    handle.write("    </aside>\n")
    handle.write("  </div>\n")
    handle.write("</section>\n\n")
    handle.write("<div class=\"section-divider\"><span>Topic Index</span></div>\n\n")


def json_to_md(filename, md_filename,
               task='',
               to_web=False,
               use_title=True,
               use_tc=True,
               show_badge=True,
               use_b2t=True,
               split_to_docs=False,
               selected_topics=None,
               page_variant="standard"):
    """Convert JSON paper store to Markdown file.

    Orchestrates the rendering pipeline by delegating to focused
    helper functions in markdown_renderer.
    """
    DateNow = str(datetime.date.today()).replace('-', '.')

    data = load_paper_store(filename)
    selected_topics = set(selected_topics or [])
    stats = compute_library_stats(data)
    topic_meta = build_topic_metadata(data)

    # Clean/create the output file
    with open(md_filename, "w+") as f:
        pass

    # Write the full Markdown document
    with open(md_filename, "a+") as f:

        # --- Jekyll front matter (web only) ---
        if use_title and to_web:
            f.write("---\nlayout: default\n---\n\n")

        is_web_landing = to_web and page_variant in {"home", "catalog"}

        # --- Badge section ---
        if show_badge and not is_web_landing:
            write_badge_section(f)

        # --- Title header ---
        if use_title and not is_web_landing:
            write_title_header(f, DateNow)
        elif not is_web_landing:
            f.write(f"> **📅 Last Updated:** `{DateNow}`\n")

        # --- Hero / landing page variants ---
        if to_web and use_title and page_variant == "home":
            write_home_hero(f, stats, DateNow)
        elif to_web and use_title and page_variant == "catalog":
            write_catalog_intro(f, stats, DateNow)
        else:
            # Standard README body
            f.write("\n![paper_list_banner](https://github.com/isLinXu/issues/assets/59380685/0ab31126-9ef4-4c49-bf80-8dae2a3acaa8)\n")
            write_introduction_section(f)
            write_features_section(f)
            write_workflow_section(f)
            write_quickstart_section(f)

        # --- Table of contents ---
        if use_tc:
            write_topic_index(f, data, to_web=to_web, split_to_docs=split_to_docs)

        # --- Paper content (topics) ---
        non_empty_topics = [(keyword, day_content) for keyword, day_content in data.items() if day_content]

        for topic_index, (keyword, day_content) in enumerate(non_empty_topics):

            if split_to_docs:
                if (not selected_topics) or (keyword in selected_topics):
                    write_monthly_archive(keyword, day_content, topic_meta, to_web, use_title)
            else:
                # Inline topic section (single-file mode)
                f.write(f"## {keyword}\n\n")
                write_paper_table(f, day_content, to_web, use_title)

                if topic_index < len(non_empty_topics) - 1:
                    f.write("\n")

                # Back-to-top link
                if use_b2t:
                    top_info = f"#Updated on {DateNow}".replace(' ', '-').replace('.', '')
                    f.write(f"<p align=right>(<a href={top_info.lower()}>back to top</a>)</p>\n\n")

        # --- Footer sections (only for main index/README, not sub-pages) ---
        if use_title and split_to_docs:
            write_footer_sections(f, to_web)

    logging.info(f"{task} finished")
