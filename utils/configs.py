import logging

import yaml


def load_config(config_file: str) -> dict:
    '''
    config_file: input config file path
    return: a dict of configuration
    '''

    # make filters pretty
    def pretty_filters(**config) -> dict:
        keywords = dict()
        EXCAPE = '\"'
        QUOTA = ''  # NO-USE
        OR = ' OR '

        def parse_filters(filters: list):
            # build arXiv query like: ("Image Classification" OR "Video Classification" OR ...)
            terms = []
            for filter in filters:
                if len(filter.split()) > 1:
                    terms.append(EXCAPE + filter + EXCAPE)
                else:
                    terms.append(filter)
            return '(' + OR.join(terms) + ')'

        for k, v in config['keywords'].items():
            keywords[k] = parse_filters(v['filters'])
        return keywords

    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        print(f'config = {config}')
        config['kv'] = pretty_filters(**config)
        logging.info(f'config = {config}')
    return config