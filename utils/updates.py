import json
import logging
import re

import requests

base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
github_url = "https://api.github.com/search/repositories"
arxiv_url = "http://arxiv.org/"
def update_paper_links(filename):
    '''
    weekly update paper links in json file
    '''

    def parse_arxiv_string(s):
        parts = s.split("|")
        date = parts[1].strip()
        title = parts[2].strip()
        authors = parts[3].strip()
        arxiv_id = parts[4].strip()
        code = parts[5].strip()
        arxiv_id = re.sub(r'v\d+', '', arxiv_id)
        return date, title, authors, arxiv_id, code

    with open(filename, "r") as f:
        content = f.read()
        if not content:
            m = {}
        else:
            m = json.loads(content)

        json_data = m.copy()

        for keywords, v in json_data.items():
            logging.info(f'keywords = {keywords}')
            for paper_id, contents in v.items():
                contents = str(contents)

                update_time, paper_title, paper_first_author, paper_url, code_url = parse_arxiv_string(contents)

                contents = "|{}|{}|{}|{}|{}|\n".format(update_time, paper_title, paper_first_author, paper_url,
                                                       code_url)
                json_data[keywords][paper_id] = str(contents)
                logging.info(f'paper_id = {paper_id}, contents = {contents}')

                valid_link = False if '|null|' in contents else True
                if valid_link:
                    continue
                try:
                    code_url = base_url + paper_id  # TODO
                    r = requests.get(code_url).json()
                    repo_url = None
                    if "official" in r and r["official"]:
                        repo_url = r["official"]["url"]
                        if repo_url is not None:
                            new_cont = contents.replace('|null|', f'|**[link]({repo_url})**|')
                            logging.info(f'ID = {paper_id}, contents = {new_cont}')
                            json_data[keywords][paper_id] = str(new_cont)

                except Exception as e:
                    logging.error(f"exception: {e} with id: {paper_id}")
        # dump to json file
        with open(filename, "w") as f:
            json.dump(json_data, f, indent=4)

def update_json_file(filename, data_dict):
    '''
    daily update json file using data_dict
    '''
    with open(filename, "r") as f:
        content = f.read()
        if not content:
            m = {}
        else:
            m = json.loads(content)

    json_data = m.copy()

    # update papers in each keywords
    for data in data_dict:
        for keyword in data.keys():
            papers = data[keyword]

            if keyword in json_data.keys():
                json_data[keyword].update(papers)
            else:
                json_data[keyword] = papers

    with open(filename, "w") as f:
        json.dump(json_data, f, indent=4)