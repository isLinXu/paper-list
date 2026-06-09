import logging
import os
from pathlib import Path

import yaml


# Default values that can be overridden via environment variables.
# This allows fork owners to configure without editing config.yaml.
_ENV_OVERRIDES = {
    "user_name":          "PAPER_LIST_USER",
    "repo_name":          "PAPER_LIST_REPO",
    "max_results":        "PAPER_LIST_MAX_RESULTS",
    "publish_readme":     "PAPER_LIST_PUBLISH_README",
    "publish_gitpage":    "PAPER_LIST_PUBLISH_GITPAGE",
    "publish_wechat":     "PAPER_LIST_PUBLISH_WECHAT",
    "show_badge":         "PAPER_LIST_SHOW_BADGE",
    "start_date":         "PAPER_LIST_START_DATE",
    "end_date":           "PAPER_LIST_END_DATE",
    "concurrent_fetch":   "PAPER_LIST_CONCURRENT_FETCH",
    "max_workers":        "PAPER_LIST_MAX_WORKERS",
    "deduplicate":        "PAPER_LIST_DEDUPLICATE",
    "enrich_tldr":        "PAPER_LIST_ENRICH_TLDR",
    "enrich_citations":   "PAPER_LIST_ENRICH_CITATIONS",
    "sort_mode":          "PAPER_LIST_SORT_MODE",
}

# Built-in profile directory
PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"

# Track whether .env has been loaded to avoid duplicate loading
_env_loaded = False


def _load_dotenv() -> None:
    """Load .env file from project root into os.environ (if not already loaded).

    This is a minimal dotenv loader — it does NOT override existing env vars,
    matching the standard dotenv convention. It also supports:
    - Comments (lines starting with #)
    - Empty lines
    - Quoted values (single or double)
    - Inline comments after values

    Requires no external dependency (no python-dotenv needed).
    """
    global _env_loaded
    if _env_loaded:
        return

    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / ".env"

    if not dotenv_path.exists():
        _env_loaded = True
        return

    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue
            # Parse KEY=VALUE
            if "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()
            # Remove surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # Strip inline comments (only if not quoted)
            if "#" in value and not value.startswith('"'):
                value = value.split("#")[0].strip()
            # Don't override existing env vars (standard dotenv convention)
            if key and key not in os.environ:
                os.environ[key] = value

    _env_loaded = True


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


def _load_profile(profile_name: str) -> dict | None:
    """Load a preset profile from the profiles/ directory.

    Supported profiles: minimal, vision, nlp_llm, robotics, full
    Returns None if the profile does not exist.
    """
    profile_path = PROFILES_DIR / f"{profile_name}.yaml"
    if not profile_path.exists():
        logging.warning(f"Profile '{profile_name}' not found at {profile_path}")
        return None
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _filter_disabled_topics(config: dict) -> dict:
    """Remove keywords with enabled: false, allowing incremental topic adoption.

    Topics without an 'enabled' key default to enabled (True).
    Disabled topics are logged so the user knows what was skipped.
    """
    keywords = config.get("keywords", {})
    disabled = []
    for topic in list(keywords.keys()):
        spec = keywords[topic]
        if isinstance(spec, dict) and not spec.get("enabled", True):
            disabled.append(topic)
            del keywords[topic]

    if disabled:
        logging.info(f"Disabled topics (enabled: false): {disabled}")

    # Also remove disabled topics from topic_groups
    topic_groups = config.get("topic_groups")
    if topic_groups:
        disabled_set = set(disabled)
        filtered_groups = []
        for group in topic_groups:
            if isinstance(group, (list, tuple)) and len(group) == 4:
                eyebrow, title, css, topics = group
                filtered_topics = [t for t in topics if t not in disabled_set]
                if filtered_topics:
                    filtered_groups.append([eyebrow, title, css, filtered_topics])
                else:
                    logging.info(f"Topic group '{title}' removed (all topics disabled)")
            else:
                filtered_groups.append(group)
        config["topic_groups"] = filtered_groups

    return config


def _ensure_site_config(config: dict) -> dict:
    """Ensure the 'site' section exists with sensible defaults.

    This centralizes all hardcoded URLs so that markdown_renderer.py
    and other modules can read them from config instead of hardcoding.
    """
    if "site" not in config:
        config["site"] = {}

    site = config["site"]
    user = config.get("user_name", "isLinXu")
    repo = config.get("repo_name", "paper-list")

    site.setdefault("github_owner", user)
    site.setdefault("github_repo", repo)
    site.setdefault("pages_url", f"https://{user}.github.io/{repo}/")

    return config


def load_config(config_file: str) -> dict:
    '''Load configuration with profile support, topic filtering, and site defaults.

    Supports:
    - profile: "minimal" → loads profiles/minimal.yaml as base, then overlays config.yaml
    - enabled: false → skips that topic without deleting its config
    - site: → centralized URL config for badges and links
    - Environment variable overrides (PAPER_LIST_*)

    config_file: input config file path
    return: a dict of configuration
    '''

    # make filters pretty
    def pretty_filters(**config) -> dict:
        keywords = dict()
        EXCAPE = '"'
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

        # --- Profile support ---
        # If config specifies a profile, load it as base and overlay current config on top
        profile_name = config.get("profile")
        if profile_name:
            profile = _load_profile(profile_name)
            if profile:
                # Profile is the base; config.yaml overrides it
                merged = {**profile, **config}
                # Deep-merge keywords (config.yaml wins per-key)
                if "keywords" in profile and "keywords" in config:
                    merged_keywords = {**profile["keywords"], **config["keywords"]}
                    merged["keywords"] = merged_keywords
                config = merged
                logging.info(f"Loaded profile '{profile_name}' as base config")

        # Load .env file before applying env overrides
        _load_dotenv()

        config = _apply_env_overrides(config)
        config = _filter_disabled_topics(config)
        config = _ensure_site_config(config)
        config['kv'] = pretty_filters(**config)
        logging.info(f'config loaded: topics={list(config.get("keywords", {}).keys())}')
    return config