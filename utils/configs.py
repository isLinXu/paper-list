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
        OR = 'OR'  # TODO

        def parse_filters(filters: list):
            ret = ''
            for idx in range(0, len(filters)):
                filter = filters[idx]
                if len(filter.split()) > 1:
                    ret += (EXCAPE + filter + EXCAPE)
                else:
                    ret += (QUOTA + filter + QUOTA)
                if idx != len(filters) - 1:
                    ret += OR
            return ret

        for k, v in config['keywords'].items():
            keywords[k] = parse_filters(v['filters'])
        return keywords

    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        print(f'config = {config}')
        config['kv'] = pretty_filters(**config)
        logging.info(f'config = {config}')
    return config