import logging
import os

import yaml


# Default values that can be overridden via environment variables.
# This allows fork owners to configure without editing config.yaml.
_ENV_OVERRIDES = {
    "user_name":       "PAPER_LIST_USER",
    "repo_name":       "PAPER_LIST_REPO",
    "max_results":     "PAPER_LIST_MAX_RESULTS",
    "publish_readme":  "PAPER_LIST_PUBLISH_README",
    "publish_gitpage": "PAPER_LIST_PUBLISH_GITPAGE",
    "publish_wechat":  "PAPER_LIST_PUBLISH_WECHAT",
    "show_badge":      "PAPER_LIST_SHOW_BADGE",
    "start_date":      "PAPER_LIST_START_DATE",
    "end_date":        "PAPER_LIST_END_DATE",
}


def _apply_env_overrides(config: dict) -> dict:
    """Override config values from environment variables when set.

    Environment variables take precedence over config.yaml values,
    making it easy to customize behavior in CI/CD without editing files.
    """
    for config_key, env_var in _ENV_OVERRIDES.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            original = config.get(config_key)
            # Type coercion: match the original type from config.yaml
            if isinstance(original, bool):
                config[config_key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(original, int):
                config[config_key] = int(env_val)
            elif original is None and env_val:
                config[config_key] = env_val
            else:
                config[config_key] = env_val
            if original != config[config_key]:
                logging.info(f"Config override: {config_key}={config[config_key]} (from {env_var})")
    return config


def load_config(config_file: str) -> dict:
    '''
    config_file: input config file path
    return: a dict of configuration
    '''

    # make filters pretty
    def pretty_filters(**config) -> dict:
        keywords = dict()
        EXCAPE = '\"'
        OR = ' OR '

        def parse_filters(filters: list):
            # build arXiv query like: "Image Classification" OR "Video Classification" OR ...
            terms = []
            for filter in filters:
                if len(filter.split()) > 1:
                    terms.append(EXCAPE + filter + EXCAPE)
                else:
                    terms.append(filter)
            # remove outer parentheses to avoid extra bracket at end of URL
            return OR.join(terms)

        for k, v in config['keywords'].items():
            keywords[k] = parse_filters(v['filters'])
        return keywords

    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        config = _apply_env_overrides(config)
        config['kv'] = pretty_filters(**config)
        logging.info(f'config loaded: topics={list(config.get("keywords", {}).keys())}')
    return config