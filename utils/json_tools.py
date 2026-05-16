import datetime
import logging
import re
import os
from collections import defaultdict

from .paper_links import ensure_paper_record, render_paper_row
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


def sort_papers(papers: dict) -> dict:
    """Sort papers by key in reverse order (newest first)."""
    output = {}
    keys = sorted(papers.keys(), reverse=True)
    for key in keys:
        output[key] = papers[key]
    return output


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
    """
    @param filename: str
    @param md_filename: str
    @return None
    """

    def pretty_math(s: str) -> str:
        ret = ''
        match = re.search(r"\$.*\$", s)
        if match == None:
            return s
        math_start, math_end = match.span()
        space_trail = space_leading = ''
        if s[:math_start][-1] != ' ' and '*' != s[:math_start][-1]: space_trail = ' '
        if s[math_end:][0] != ' ' and '*' != s[math_end:][0]: space_leading = ' '
        ret += s[:math_start]
        ret += f'{space_trail}${match.group()[1:-1].strip()}${space_leading}'
        ret += s[math_end:]
        return ret

    DateNow = datetime.date.today()
    DateNow = str(DateNow)
    DateNow = DateNow.replace('-', '.')

    data = load_paper_store(filename)
    selected_topics = set(selected_topics or [])
    stats = compute_library_stats(data)

    def group_papers_by_month(papers: dict) -> dict:
        grouped = defaultdict(dict)
        for paper_id, entry in sort_papers(papers).items():
            record = ensure_paper_record(entry, paper_id=paper_id)
            grouped[record["date"][:7]][paper_id] = record
        return dict(grouped)

    # clean README.md if daily already exist else create it
    with open(md_filename, "w+") as f:
        pass

    # write data into README.md
    with open(md_filename, "a+") as f:

        if (use_title == True) and (to_web == True):
            f.write("---\n" + "layout: default\n" + "---\n\n")

        is_web_landing = to_web and page_variant in {"home", "catalog"}

        if show_badge == True and not is_web_landing:
            # Row 1: Project identity + GitHub stats
            f.write("![paper-list](https://github.com/isLinXu/issues/assets/59380685/dbd27f25-e7d7-4a0f-bdc2-d9b06fc03a2e) ")
            f.write("![GitHub stars](https://img.shields.io/github/stars/isLinXu/paper-list?style=flat-square&color=ffd700) ")
            f.write("![GitHub forks](https://img.shields.io/github/forks/isLinXu/paper-list?style=flat-square&color=4ecdc4) ")
            f.write("![GitHub watchers](https://img.shields.io/github/watchers/isLinXu/paper-list?style=flat-square&color=ff6b6b)\n")
            # Row 2: Build + quality + repo metrics
            f.write("[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fatrox%2Fsync-dotenv%2Fbadge&style=flat-square)](https://github.com/isLinXu/paper-list) ")
            f.write("![GitHub last commit](https://img.shields.io/github/last-commit/isLinXu/paper-list?style=flat-square&color=a8e6cf) ")
            f.write("![GitHub repo size](https://img.shields.io/github/repo-size/isLinXu/paper-list.svg?style=flat-square&color=ffd3b6) ")
            f.write("![GitHub language count](https://img.shields.io/github/languages/count/isLinXu/paper-list?style=flat-square&color=ffaaa5)\n")
            # Row 3: License + hits
            f.write("![GitHub](https://img.shields.io/github/license/isLinXu/paper-list.svg?style=flat-square&color=c7ceea) ")
            f.write("![Hits](https://hits.dwyl.com/isLinXu/paper-list.svg?style=flat-square&color=95e1d3)\n")

        if use_title == True and not is_web_landing:
            f.write('\n<h1 align="center">📜 Paper-List-DAILY</h1>\n')
            f.write('<p align="center"><strong>Automatically track & organize the latest arXiv papers by topic — updated daily via GitHub Actions</strong></p>\n')
            f.write('\n<p align="center">')
            f.write('<a href="https://islinxu.github.io/paper-list/"><img alt="Website" src="https://img.shields.io/badge/🌐_Live_Site-Visit_Now-0f4c5c?style=for-the-badge"></a> ')
            f.write('<a href="https://github.com/isLinXu/paper-list/stargazers"><img alt="Stargazers" src="https://img.shields.io/badge/⭐_Star_Us-ff6b6b?style=for-the-badge"></a>')
            f.write('</p>\n')
            f.write('\n---\n')
            f.write('\n> **📅 Last Updated:** `' + DateNow + '` · **🤖 Auto-generated by GitHub Actions**\n')
        elif not is_web_landing:
            f.write("> **📅 Last Updated:** `" + DateNow + "`\n")

        if to_web and use_title and page_variant == "home":
            write_home_hero(f, stats, DateNow)
        elif to_web and use_title and page_variant == "catalog":
            write_catalog_intro(f, stats, DateNow)
        else:
            f.write(f"\n")
            f.write("![paper_list_banner](https://github.com/isLinXu/issues/assets/59380685/0ab31126-9ef4-4c49-bf80-8dae2a3acaa8)\n")

            # Add Introduction
            f.write("\n## 📖 Introduction\n\n")
            f.write("**Paper-List-DAILY** is an automated arXiv paper tracking system that fetches, categorizes, and organizes the latest research papers across **20+ computer vision & AI topics** — from classic tasks like Object Detection and Segmentation to cutting-edge fields like Diffusion Models, LLMs, and Embodied AI.\n\n")
            f.write("Every day, GitHub Actions automatically polls the [Papers with Code API](https://paperswithcode.com/), enriches paper metadata with arXiv links, translation services, and code repositories, then generates beautifully formatted Markdown lists for both GitHub README and GitHub Pages.\n\n")
            f.write("🌐 **Online Documentation:** [https://islinxu.github.io/paper-list/](https://islinxu.github.io/paper-list/)\n\n")

            # Add Features
            f.write("## ✨ Features\n\n")
            f.write("| Feature | Description |\n")
            f.write("|---------|-------------|\n")
            f.write("| 🔄 **Daily Auto-Update** | Runs every 8 hours via GitHub Actions — zero manual intervention |\n")
            f.write("| 📂 **20+ Research Topics** | From Classification to Embodied AI, covering the full CV/AI spectrum |\n")
            f.write("| 📊 **Research Insights Entry** | Trend charts, topic rankings, top authors, and code coverage in a separate analytics section |\n")
            f.write("| 🔗 **Smart Link Enrichment** | Auto-attaches arXiv PDF, translation (papers.cool), reading (hjfy), and code links |\n")
            f.write("| 📱 **Dual Output** | Generates both GitHub README and Jekyll-powered GitHub Pages |\n")
            f.write("| 🎨 **Three Visual Themes** | Editorial (warm), Atlas (dark), Lab (clean) — switchable on the site |\n")
            f.write("| 🔍 **Configurable Keywords** | Fully customizable search filters via `config.yaml` |\n")
            f.write("| 📈 **Monthly Archives** | Papers organized by month for easy historical browsing |\n")
            f.write("| 🌐 **Multi-language Support** | Integrated paper translation links for non-English readers |\n\n")

            # Add Workflow
            f.write("## 🏗️ How It Works\n\n")
            f.write("```\n┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐\n")
            f.write("│  Papers with    │────▶│  GitHub Actions │────▶│  Enriched MD    │\n")
            f.write("│  Code API       │     │  (every 8h)     │     │  + Analytics    │\n")
            f.write("└─────────────────┘     └─────────────────┘     └─────────────────┘\n")
            f.write("         │                       │                       │\n")
            f.write("         ▼                       ▼                       ▼\n")
            f.write("   📥 Fetch Papers        🔗 Enrich Links         📝 Generate\n")
            f.write("   🔍 Filter by Topic     📊 Build Analytics      🌐 GitHub Pages\n")
            f.write("   📅 Sort by Date        💾 Store JSON           📄 README.md\n")
            f.write("```\n\n")

            # Add Analytics入口（静态图 + 交互页）
            if to_web:
                analytics_href = "analytics/"
                charts_prefix = "analytics/charts/"
            else:
                analytics_href = "docs/analytics/"
                charts_prefix = "docs/analytics/charts/"

            # Add Usage Instructions
            f.write("## 🚀 Quick Start\n\n")
            f.write("### Prerequisites\n\n")
            f.write("- Python 3.10+\n")
            f.write("- pip\n\n")
            f.write("### Installation\n\n")
            f.write("1. **Clone the repository**\n")
            f.write("   ```bash\n")
            f.write("   git clone https://github.com/isLinXu/paper-list.git\n")
            f.write("   cd paper-list\n")
            f.write("   ```\n\n")
            f.write("2. **Install Dependencies**\n")
            f.write("   ```bash\n")
            f.write("   pip install -r requirements.txt\n")
            f.write("   ```\n\n")
            f.write("3. **Run the Script**\n")
            f.write("   ```bash\n")
            f.write("   # Fetch papers from the last 2 days\n")
            f.write("   python get_paper.py\n\n")
            f.write("   # Or specify a date range\n")
            f.write("   python get_paper.py --start_date 2024-01-01 --end_date 2024-12-31\n")
            f.write("   ```\n\n")
            f.write("4. **Configuration**\n")
            f.write("   Customize search keywords, output paths, and more in [`config.yaml`](config.yaml):\n")
            f.write("   ```yaml\n")
            f.write("   keywords:\n")
            f.write("     \"Object Detection\":\n")
            f.write("       filters: [\"Object Detection\", \"2D Object Detection\", \"3D Object Detection\"]\n")
            f.write("     \"Diffusion Models\":\n")
            f.write("       filters: [\"Diffusion Model\", \"Stable Diffusion\", \"DALL-E\"]\n")
            f.write("   ```\n\n")

            # Add Advanced Usage
            f.write("### 🔧 Advanced Usage\n\n")
            f.write("| Command | Description |\n")
            f.write("|---------|-------------|\n")
            f.write("| `python get_paper.py --update_paper_links` | Enrich existing papers with code links |\n")
            f.write("| `python scripts/count_range.py 2024-01-01 2024-12-31` | Count papers in a date range |\n")
            f.write("| `python scripts/build_analytics.py --store docs/data --out docs/analytics` | Build the separate research insights dashboard |\n")
            f.write("| `./scripts/serve_pages.sh` | Install local Jekyll deps and preview GitHub Pages at `127.0.0.1:4000` |\n")
            f.write("| `python regenerate_readme.py` | Regenerate README from existing JSON data |\n\n")

        # Add: table of contents
        if use_tc == True:
            write_topic_index(f, data, to_web=to_web, split_to_docs=split_to_docs)

        non_empty_topics = [(keyword, day_content) for keyword, day_content in data.items() if day_content]

        for topic_index, (keyword, day_content) in enumerate(non_empty_topics):

            if split_to_docs:
                if not os.path.exists('docs'):
                    os.makedirs('docs')
                kw = keyword.replace(' ', '_')
                if (not selected_topics) or (keyword in selected_topics):
                    with open(f"docs/{kw}.md", "w+") as f_sub:
                        f_sub.write(f"## {keyword}\n\n")
                        grouped = group_papers_by_month(day_content)
                        total_papers = sum(len(month_items) for month_items in grouped.values())
                        f_sub.write(f"Total papers: **{total_papers}**\n\n")
                        f_sub.write("## Monthly Archives\n\n")
                        for month, month_items in sorted(grouped.items(), reverse=True):
                            month_dir = os.path.join("docs", kw)
                            os.makedirs(month_dir, exist_ok=True)
                            month_file = os.path.join(month_dir, f"{month}.md")
                            month_href = f"{kw}/{month}.md" if to_web else f"{kw}/{month}.md"
                            f_sub.write(f"- [{month}]({month_href}) ({len(month_items)} papers)\n")

                            with open(month_file, "w+") as month_sub:
                                month_sub.write(f"## {keyword} - {month}\n\n")
                                if use_title == True:
                                    if to_web == False:
                                        month_sub.write("|Publish Date|Title|Authors|PDF|Translate|Read|Code|\n" + "|---|---|---|---|---|---|---|\n")
                                    else:
                                        month_sub.write("| Publish Date | Title | Authors | PDF | Translate | Read | Code |\n")
                                        month_sub.write("|:---------|:-----------------------|:---------|:------|:------|:------|:------|\n")

                                for _, v in sort_papers(month_items).items():
                                    if v is not None:
                                        line = render_paper_row(v, emphasize=False) if isinstance(v, dict) else str(v)
                                        month_sub.write(pretty_math(line))

                                month_sub.write(f"\n<p align=right>(<a href=../{kw}.md>back to {keyword}</a>)</p>\n\n")

                        back_target = "index.md" if to_web else "../README.md"
                        f_sub.write(f"\n<p align=right>(<a href={back_target}>back to main</a>)</p>\n\n")
            else:
                # the head of each part
                f.write(f"## {keyword}\n\n")

                if use_title == True:
                    if to_web == False:
                        f.write("|Publish Date|Title|Authors|PDF|Translate|Read|Code|\n" + "|---|---|---|---|---|---|---|\n")
                    else:
                        f.write("| Publish Date | Title | Authors | PDF | Translate | Read | Code |\n")
                        f.write("|:---------|:-----------------------|:---------|:------|:------|:------|:------|\n")

                # sort papers by date
                day_content = sort_papers(day_content)

                for _, v in day_content.items():
                    if v is not None:
                        line = render_paper_row(v, emphasize=False) if isinstance(v, dict) else str(v)
                        f.write(pretty_math(line))  # make latex pretty

                if topic_index < len(non_empty_topics) - 1:
                    f.write("\n")

                # Add: back to top
                if use_b2t:
                    top_info = f"#Updated on {DateNow}"
                    top_info = top_info.replace(' ', '-').replace('.', '')
                    f.write(f"<p align=right>(<a href={top_info.lower()}>back to top</a>)</p>\n\n")

        # Add footer sections (only for main index/README, not sub-pages)
        if use_title == True and split_to_docs:
            # Add Insights section
            if to_web:
                analytics_href = "analytics/"
                charts_prefix = "analytics/charts/"
            else:
                analytics_href = "docs/analytics/"
                charts_prefix = "docs/analytics/charts/"

            f.write("\n---\n\n")
            f.write("## 📊 Research Insights\n\n")
            f.write("Analytics is available as a separate entrance so the main reading flow stays topic-first.\n\n")
            f.write(f"- **Insights Dashboard:** [{analytics_href}]({analytics_href})\n")
            f.write("- **Daily Trend:** Papers published per day\n")
            f.write("- **Topic Ranking:** Most active research areas\n")
            f.write("- **Top Authors:** Most prolific researchers\n")
            f.write("- **Code Coverage:** Ratio of papers with open-source code\n\n")
            f.write("<details>\n")
            f.write("<summary>Preview charts</summary>\n\n")
            f.write(f"![trend_daily]({charts_prefix}trend_daily.png)\n\n")
            f.write(f"![topic_rank]({charts_prefix}topic_rank.png)\n\n")
            f.write("</details>\n\n")

            # Add Star History
            f.write("\n---\n\n")
            f.write("## ⭐ Star History\n\n")
            f.write("[![Star History Chart](https://api.star-history.com/svg?repos=isLinXu/paper-list&type=Date)](https://star-history.com/#isLinXu/paper-list&Date)\n\n")
            f.write("> If you find this project helpful, please consider giving it a ⭐ — it helps others discover the project!\n\n")

            # Add Contributing
            f.write("\n---\n\n")
            f.write("## 🤝 Contributing\n\n")
            f.write("We welcome contributions! Here are some ways you can help:\n\n")
            f.write("- **🐛 Report Issues:** Found a bug or missing paper? [Open an issue](https://github.com/isLinXu/paper-list/issues)\n")
            f.write("- **💡 Suggest Topics:** Want a new research category? Propose it in the issues\n")
            f.write("- **🔧 Improve Code:** Submit a PR to enhance the scraper, analytics, or UI\n")
            f.write("- **📖 Improve Docs:** Help us write better documentation\n\n")
            f.write("### Development Setup\n\n")
            f.write("```bash\n")
            f.write("# Fork and clone\n")
            f.write("git clone https://github.com/<your-username>/paper-list.git\n")
            f.write("cd paper-list\n\n")
            f.write("# Install dependencies\n")
            f.write("pip install -r requirements.txt\n\n")
            f.write("# Run tests\n")
            f.write("python -m pytest tests/\n")
            f.write("```\n\n")

            # Add License
            f.write("\n---\n\n")
            f.write("## 📄 License\n\n")
            f.write("This project is licensed under the [Apache License 2.0](LICENSE).\n\n")
            f.write("The paper data is sourced from [arXiv](https://arxiv.org/) and [Papers with Code](https://paperswithcode.com/), ")
            f.write("and remains subject to their respective terms of use.\n\n")

            # Add Acknowledgements
            f.write("\n---\n\n")
            f.write("## 🙏 Acknowledgements\n\n")
            f.write("- [arXiv](https://arxiv.org/) — for providing open access to research papers\n")
            f.write("- [Papers with Code](https://paperswithcode.com/) — for the comprehensive paper API\n")
            f.write("- [papers.cool](https://papers.cool/) — for paper translation services\n")
            f.write("- [hjfy.top](https://hjfy.top/) — for enhanced paper reading experience\n\n")

            # Final footer
            f.write("\n---\n\n")
            f.write("<p align=\"center\">\n")
            f.write("  <sub>Built with ❤️ by <a href=\"https://github.com/isLinXu\">@isLinXu</a> · Powered by GitHub Actions</sub>\n")
            f.write("</p>\n")

    logging.info(f"{task} finished")
