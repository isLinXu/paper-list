#!/usr/bin/env python3
"""
Config validator for paper-list.

Checks:
1. user_name / repo_name are not placeholder values
2. All topics in TOPIC_GROUPS exist in config keywords
3. No duplicate filter terms within a topic
4. start_date format is valid (if set)
5. Cross-topic filter overlap detection
6. Orphan topics (in keywords but not in TOPIC_GROUPS)
7. Environment variable overrides are valid
8. Output paths are writable

Usage:
    python scripts/validate_config.py
    python scripts/validate_config.py --config path/to/config.yaml
    python scripts/validate_config.py --strict   # treat warnings as errors
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

# These topic names are the default when config.yaml does not define topic_groups.
# Now that topic_groups can be configured in config.yaml, this is only a fallback.
BUILTIN_TOPIC_GROUPS = [
    ["Classification", "Object Detection", "Semantic Segmentation", "Anomaly Detection"],
    ["Object Tracking", "Action Recognition", "Pose Estimation", "Depth Estimation", "Optical Flow"],
    ["Image Generation", "Diffusion Models", "LLM", "Latent Space LLM", "Multimodal"],
    [
        "Scene Understanding", "Video Understanding", "Neural Rendering",
        "Transfer Learning", "Reinforcement Learning", "Graph Neural Networks", "Audio Processing",
    ],
]


def _get_effective_topic_groups(config: dict) -> list[list[str]]:
    """Get topic groups from config, falling back to BUILTIN_TOPIC_GROUPS."""
    raw_groups = config.get("topic_groups")
    if raw_groups:
        groups = []
        for item in raw_groups:
            if isinstance(item, (list, tuple)) and len(item) == 4:
                groups.append(item[3])  # 4th element is the topic list
        if groups:
            return groups
    return BUILTIN_TOPIC_GROUPS

PLACEHOLDER_USERNAMES = {"isLinXu", "CHANGE_ME"}
PLACEHOLDER_REPONAMES = {"YOUR_REPO_NAME", "cv-arxiv-daily", "CHANGE_ME"}

# Environment variable override mapping (must match utils/configs.py)
ENV_OVERRIDES = {
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


def validate_config(config_path: str, strict: bool = False) -> list[str]:
    warnings: list[str] = []
    errors: list[str] = []
    infos: list[str] = []

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 1. Check user_name / repo_name
    user_name = config.get("user_name", "")
    repo_name = config.get("repo_name", "")

    # Check env override first
    env_user = os.environ.get("PAPER_LIST_USER")
    env_repo = os.environ.get("PAPER_LIST_REPO")

    effective_user = env_user or user_name
    effective_repo = env_repo or repo_name

    if env_user:
        infos.append(f"[INFO] user_name overridden by PAPER_LIST_USER={env_user}")
    if env_repo:
        infos.append(f"[INFO] repo_name overridden by PAPER_LIST_REPO={env_repo}")

    if effective_user in PLACEHOLDER_USERNAMES:
        errors.append(
            f"[ERROR] config.yaml: user_name='{effective_user}' looks like a placeholder. "
            "Please set it to your actual GitHub username "
            "(edit config.yaml or set PAPER_LIST_USER env var)."
        )
    if effective_repo in PLACEHOLDER_REPONAMES:
        warnings.append(
            f"[WARN]  config.yaml: repo_name='{effective_repo}' looks like a placeholder. "
            "Please set it to your actual repository name "
            "(edit config.yaml or set PAPER_LIST_REPO env var)."
        )

    keywords: dict = config.get("keywords") or {}

    # 2. Check TOPIC_GROUPS topics exist in keywords
    effective_groups = _get_effective_topic_groups(config)
    all_grouped = [topic for group in effective_groups for topic in group]
    for topic in all_grouped:
        if topic not in keywords:
            warnings.append(
                f"[WARN]  topic_groups references topic '{topic}' which is NOT in config.yaml keywords. "
                "It will be silently skipped in GitHub Pages topic lanes."
            )

    # 3. Check for orphan topics (in keywords but not in topic_groups)
    grouped_set = set(all_grouped)
    for topic in keywords:
        if topic not in grouped_set:
            infos.append(
                f"[INFO] Topic '{topic}' is in keywords but NOT in topic_groups. "
                "It will appear after grouped topics in the output. "
                "Add it to topic_groups in config.yaml if you want it in a lane."
            )

    # 4. Check for duplicate filters within a topic
    for topic, spec in keywords.items():
        filters = spec.get("filters", []) if isinstance(spec, dict) else []
        seen: set[str] = set()
        for f in filters:
            normalized = f.strip().lower()
            if normalized in seen:
                warnings.append(
                    f"[WARN]  keywords['{topic}']: duplicate filter '{f}' - "
                    "remove one to avoid redundant API queries."
                )
            seen.add(normalized)

    # 5. Cross-topic filter overlap detection
    filter_to_topics: dict[str, list[str]] = {}
    for topic, spec in keywords.items():
        filters = spec.get("filters", []) if isinstance(spec, dict) else []
        for f in filters:
            normalized = f.strip().lower()
            filter_to_topics.setdefault(normalized, []).append(topic)

    overlapping = {f: topics for f, topics in filter_to_topics.items() if len(topics) > 1}
    if overlapping:
        infos.append(f"[INFO] {len(overlapping)} filter terms appear in multiple topics:")
        for f, topics in sorted(overlapping.items()):
            infos.append(f"       '{f}' -> {', '.join(topics)}")
        infos.append("       This is normal for broad terms but may cause duplicate papers.")

    # 6. Check start_date format
    start_date = config.get("start_date")
    if start_date is not None:
        try:
            import datetime
            datetime.date.fromisoformat(str(start_date))
            warnings.append(
                f"[WARN]  config.yaml: start_date='{start_date}' is a fixed past date. "
                "This causes full re-scan on local runs. Consider setting start_date: null."
            )
        except (ValueError, TypeError):
            errors.append(f"[ERROR] config.yaml: start_date='{start_date}' is not a valid YYYY-MM-DD date.")

    # 7. Check max_results sanity
    max_results = config.get("max_results", 100)
    if isinstance(max_results, int) and max_results > 500:
        warnings.append(
            f"[WARN]  config.yaml: max_results={max_results} is very large. "
            "This may cause slow runs and API rate limits. Consider 100-200."
        )

    # 8. Check environment variable overrides are valid
    for config_key, env_var in ENV_OVERRIDES.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            original = config.get(config_key)
            if isinstance(original, bool):
                if env_val.lower() not in ("true", "false", "1", "0", "yes", "no"):
                    errors.append(
                        f"[ERROR] Environment variable {env_var}='{env_val}' is not a valid boolean. "
                        "Use true/false, 1/0, or yes/no."
                    )
            elif isinstance(original, int):
                try:
                    int(env_val)
                except ValueError:
                    errors.append(
                        f"[ERROR] Environment variable {env_var}='{env_val}' is not a valid integer."
                    )

    # 9. Check output paths are writable
    for path_key in ("json_readme_path", "md_readme_path", "json_gitpage_path", "md_gitpage_path"):
        path_val = config.get(path_key)
        if path_val:
            parent = Path(path_val).parent
            if parent and not parent.exists():
                infos.append(
                    f"[INFO] Output directory for {path_key}='{path_val}' does not exist yet. "
                    "It will be created automatically."
                )

    # 10. Check keyword count and estimate runtime
    topic_count = len(keywords)
    total_filters = sum(
        len(spec.get("filters", [])) if isinstance(spec, dict) else 0
        for spec in keywords.values()
    )

    # Count disabled topics
    disabled_count = 0
    for topic, spec in keywords.items():
        if isinstance(spec, dict) and not spec.get("enabled", True):
            disabled_count += 1

    enabled_count = topic_count - disabled_count
    infos.append(
        f"[INFO] Configuration summary: {enabled_count} active topics, "
        f"{disabled_count} disabled, {total_filters} total filter terms"
    )
    if topic_count > 25:
        warnings.append(
            f"[WARN]  {topic_count} topics is a lot. Each topic requires a separate arXiv API call. "
            "Consider reducing topics or disabling some with 'enabled: false'."
        )

    # 11. Check profile validity
    profile_name = config.get("profile")
    if profile_name:
        profiles_dir = Path(__file__).resolve().parent.parent / "profiles"
        profile_path = profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
            errors.append(
                f"[ERROR] Profile '{profile_name}' not found at {profile_path}. "
                "Available profiles: minimal, vision, nlp_llm, robotics, full"
            )
        else:
            infos.append(f"[INFO] Using profile: {profile_name}")

    # 12. Check site config completeness
    site = config.get("site", {})
    if not site:
        infos.append(
            "[INFO] No 'site' section in config.yaml. "
            "Badge URLs will use hardcoded defaults. "
            "Add a 'site:' section for automatic URL management."
        )

    # 13. Check docs/_config.yml for stale upstream references
    jekyll_config_path = Path(config_path).resolve().parent / "docs" / "_config.yml"
    if jekyll_config_path.exists():
        jekyll_content = jekyll_config_path.read_text(encoding="utf-8")
        stale_refs = []
        if "isLinXu" in jekyll_content:
            stale_refs.append("isLinXu (upstream owner)")
        if "github.com/isLinXu/paper-list" in jekyll_content:
            stale_refs.append("upstream repository URL")
        if stale_refs:
            warnings.append(
                f"[WARN]  docs/_config.yml still contains upstream references: "
                f"{', '.join(stale_refs)}. "
                "Run 'python scripts/setup_fork.py' to auto-fix, "
                "or manually update the URLs to match your fork."
            )

    # 14. Check for .env file existence
    dot_env_path = Path(config_path).resolve().parent / ".env"
    dot_env_example = Path(config_path).resolve().parent / ".env.example"
    if dot_env_example.exists() and not dot_env_path.exists():
        infos.append(
            "[INFO] No .env file found. Create one from .env.example: "
            "cp .env.example .env  (then fill in your values)"
        )

    # 15. Check profile consistency (profile keywords vs config keywords)
    profile_name = config.get("profile")
    if profile_name:
        profiles_dir = Path(__file__).resolve().parent.parent / "profiles"
        profile_path = profiles_dir / f"{profile_name}.yaml"
        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as pf:
                profile_config = yaml.safe_load(pf)
            profile_topics = set((profile_config or {}).get("keywords", {}).keys())
            config_topics = set(keywords.keys())
            # Topics in profile but not in config (removed by user intentionally — OK)
            # Topics in config but not in profile (added by user — OK, just note it)
            new_topics = config_topics - profile_topics
            if new_topics:
                infos.append(
                    f"[INFO] Profile '{profile_name}' has been extended with "
                    f"{len(new_topics)} extra topic(s): {sorted(new_topics)}"
                )

    # 16. Check concurrent_fetch consistency
    concurrent = config.get("concurrent_fetch", True)
    workers = config.get("max_workers", 3)
    if not concurrent and workers > 1:
        warnings.append(
            "[WARN]  concurrent_fetch is disabled but max_workers > 1. "
            "Set concurrent_fetch: true or reduce max_workers to 1."
        )

    # 17. Check publish flags — at least one output channel should be enabled
    pub_readme = config.get("publish_readme", True)
    pub_gitpage = config.get("publish_gitpage", True)
    pub_wechat = config.get("publish_wechat", False)
    if not any([pub_readme, pub_gitpage, pub_wechat]):
        errors.append(
            "[ERROR] All publish channels are disabled (publish_readme, publish_gitpage, "
            "publish_wechat are all false). Enable at least one output channel."
        )

    all_issues = infos + errors + warnings

    if strict:
        # In strict mode, treat warnings as errors
        all_issues = [
            msg.replace("[WARN]", "[ERROR]") if "[WARN]" in msg else msg
            for msg in all_issues
        ]

    return all_issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate paper-list config.yaml")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        sys.exit(1)

    issues = validate_config(str(config_path), strict=args.strict)

    if not issues:
        print("[OK] Config validation passed - no issues found.")
        sys.exit(0)

    errors = [i for i in issues if i.startswith("[ERROR]")]
    warnings = [i for i in issues if i.startswith("[WARN]")]
    infos = [i for i in issues if i.startswith("[INFO]")]

    for msg in issues:
        print(msg)

    print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info")

    if errors:
        print("\nFix errors before running the pipeline.")
        sys.exit(1)
    else:
        print("\nAll errors resolved. Warnings are informational.")
        sys.exit(0)


if __name__ == "__main__":
    main()
