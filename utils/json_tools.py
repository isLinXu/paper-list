import datetime
import json
import logging
import re

from .sorts import sort_papers


def json_to_md(filename, md_filename,
               task='',
               to_web=False,
               use_title=True,
               use_tc=True,
               show_badge=True,
               use_b2t=True):
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

    with open(filename, "r") as f:
        content = f.read()
        if not content:
            data = {}
        else:
            data = json.loads(content)

    # clean README.md if daily already exist else create it
    with open(md_filename, "w+") as f:
        pass

    # write data into README.md
    with open(md_filename, "a+") as f:

        if (use_title == True) and (to_web == True):
            f.write("---\n" + "layout: default\n" + "---\n\n")

        if show_badge == True:
            f.write(f"[![Contributors][contributors-shield]][contributors-url]\n")
            f.write(f"[![Forks][forks-shield]][forks-url]\n")
            f.write(f"[![Stargazers][stars-shield]][stars-url]\n")
            f.write(f"[![Issues][issues-shield]][issues-url]\n\n")

        if use_title == True:
            # f.write(("<p align="center"><h1 align="center"><br><ins>CV-ARXIV-DAILY"
            #         "</ins><br>Automatically Update CV Papers Daily</h1></p>\n"))
            f.write("## Updated on " + DateNow + "\n")
        else:
            f.write("> Updated on " + DateNow + "\n")

        # TODO: add usage
        f.write("> Usage instructions: [here](./docs/README.md#usage)\n\n")

        # Add: table of contents
        if use_tc == True:
            f.write("<details>\n")
            f.write("  <summary>Table of Contents</summary>\n")
            f.write("  <ol>\n")
            for keyword in data.keys():
                day_content = data[keyword]
                if not day_content:
                    continue
                kw = keyword.replace(' ', '-')
                f.write(f"    <li><a href=#{kw.lower()}>{keyword}</a></li>\n")
            f.write("  </ol>\n")
            f.write("</details>\n\n")

        for keyword in data.keys():
            day_content = data[keyword]
            if not day_content:
                continue
            # the head of each part
            f.write(f"## {keyword}\n\n")

            if use_title == True:
                if to_web == False:
                    f.write("|Publish Date|Title|Authors|PDF|Code|\n" + "|---|---|---|---|---|\n")
                else:
                    f.write("| Publish Date | Title | Authors | PDF | Code |\n")
                    f.write("|:---------|:-----------------------|:---------|:------|:------|\n")

            # sort papers by date
            day_content = sort_papers(day_content)

            for _, v in day_content.items():
                if v is not None:
                    f.write(pretty_math(v))  # make latex pretty

            f.write(f"\n")

            # Add: back to top
            if use_b2t:
                top_info = f"#Updated on {DateNow}"
                top_info = top_info.replace(' ', '-').replace('.', '')
                f.write(f"<p align=right>(<a href={top_info.lower()}>back to top</a>)</p>\n\n")

        if show_badge == True:
            # we don't like long string, break it!
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
#            f.write((f"[contributors-shield]: https://img.shields.io/github/"
#                     f"contributors/isLinXu/paper-list.svg?style=for-the-badge\n"))
#            f.write((f"[contributors-url]: https://github.com/isLinXu/"
#                     f"paper-list/graphs/contributors\n"))
#            f.write((f"[forks-shield]: https://img.shields.io/github/forks/isLinXu/"
#                     f"paper-list.svg?style=for-the-badge\n"))
#            f.write((f"[forks-url]: https://github.com/isLinXu/"
#                     f"paper-list/network/members\n"))
#            f.write((f"[stars-shield]: https://img.shields.io/github/stars/isLinXu/"
#                     f"paper-list.svg?style=for-the-badge\n"))
#            f.write((f"[stars-url]: https://github.com/isLinXu/"
#                     f"paper-list/stargazers\n"))
#            f.write((f"[issues-shield]: https://img.shields.io/github/issues/isLinXu/"
#                     f"paper-list.svg?style=for-the-badge\n"))
#            f.write((f"[issues-url]: https://github.com/isLinXu/"
#                     f"paper-list/issues\n\n"))

    logging.info(f"{task} finished")