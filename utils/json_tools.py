import datetime
import logging
import re
import os
from collections import defaultdict

from .paper_links import ensure_paper_record, render_paper_row
from .sorts import sort_papers
from .storage import load_paper_store


def json_to_md(filename, md_filename,
               task='',
               to_web=False,
               use_title=True,
               use_tc=True,
               show_badge=True,
               use_b2t=True,
               split_to_docs=False,
               selected_topics=None):
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

        if show_badge == True:
            f.write("![paper-list](https://github.com/isLinXu/issues/assets/59380685/dbd27f25-e7d7-4a0f-bdc2-d9b06fc03a2e)")
            f.write("![GitHub stars](https://img.shields.io/github/stars/isLinXu/paper-list)")
            f.write("![GitHub forks](https://img.shields.io/github/forks/isLinXu/paper-list)")
            f.write("![GitHub watchers](https://img.shields.io/github/watchers/isLinXu/paper-list)") 
            f.write("[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fatrox%2Fsync-dotenv%2Fbadge&style=flat)](https://github.com/isLinXu/paper-list)")  
            f.write("![img](https://badgen.net/badge/icon/learning?icon=deepscan&label)") 
            f.write("![GitHub repo size](https://img.shields.io/github/repo-size/isLinXu/paper-list.svg?style=flat-square)")  
            f.write("![GitHub language count](https://img.shields.io/github/languages/count/isLinXu/paper-list)")   
            f.write("![GitHub last commit](https://img.shields.io/github/last-commit/isLinXu/paper-list)")  
            f.write("![GitHub](https://img.shields.io/github/license/isLinXu/paper-list.svg?style=flat-square)") 
            f.write("![img](https://hits.dwyl.com/isLinXu/paper-list.svg)")

        if use_title == True:
            f.write('<p align="center"><h1 align="center"><br><ins>Paper-List-DAILY'
                     '</ins><br>Automatically Update Papers Daily in list</h1></p>\n')
            f.write("## Updated on " + DateNow + "\n")
        else:
            f.write("> Updated on " + DateNow + "\n")

        f.write(f"\n")
        f.write("![paper_list](https://github.com/isLinXu/issues/assets/59380685/0ab31126-9ef4-4c49-bf80-8dae2a3acaa8)")
        
        # Add Introduction
        f.write("\n\n## Introduction\n\n")
        f.write("This repository provides a daily-updated list of computer vision papers from arXiv, organized by topic. ")
        f.write("The updates are automated using GitHub Actions to ensure you stay current with the latest research.\n\n")
        f.write("Online documentation: [https://islinxu.github.io/paper-list/](https://islinxu.github.io/paper-list/)\n\n")
        
        # Add Usage Instructions
        f.write("## Usage\n\n")
        f.write("To generate the paper list locally, follow these steps:\n\n")
        f.write("1. **Install Dependencies**\n")
        f.write("   ```bash\n")
        f.write("   pip install -r requirements.txt\n")
        f.write("   ```\n\n")
        f.write("2. **Run the Script**\n")
        f.write("   ```bash\n")
        f.write("   python get_paper.py\n")
        f.write("   ```\n\n")
        f.write("3. **Configuration**\n")
        f.write("   You can customize the search keywords and other settings in `config.yaml`.\n\n")
        
        # Add Advanced Usage
        f.write("### Advanced Usage\n\n")
        f.write("You can also use the scripts in the `scripts/` directory for additional tasks:\n\n")
        f.write("- **Count Papers in Range**: Count the number of papers within a specific date range.\n")
        f.write("  ```bash\n")
        f.write("  python scripts/count_range.py 2024-01-01 2024-12-31\n")
        f.write("  ```\n\n")

        # Add: table of contents
        if use_tc == True:
            f.write("## Paper List\n\n")
            # f.write("<details>\n")
            # f.write("  <summary>Table of Contents</summary>\n")
            f.write("  <ol>\n")
            for keyword in data.keys():
                day_content = data[keyword]
                if not day_content:
                    continue
                if split_to_docs:
                    kw = keyword.replace(' ', '_')
                    href = f"{kw}.md" if to_web else f"docs/{kw}.md"
                    f.write(f"    <li><a href={href}>{keyword}</a></li>\n")
                else:
                    kw = keyword.replace(' ', '-')
                    f.write(f"    <li><a href=#{kw.lower()}>{keyword}</a></li>\n")
            f.write("  </ol>\n")
            # f.write("</details>\n\n")

        for keyword in data.keys():
            day_content = data[keyword]
            if not day_content:
                continue

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

                f.write(f"\n")

                # Add: back to top
                if use_b2t:
                    top_info = f"#Updated on {DateNow}"
                    top_info = top_info.replace(' ', '-').replace('.', '')
                    f.write(f"<p align=right>(<a href={top_info.lower()}>back to top</a>)</p>\n\n")

    logging.info(f"{task} finished")
