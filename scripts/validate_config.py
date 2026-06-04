#!/usr/bin/env python3
"""
Config validator for paper-list.

Checks:
1. user_name / repo_name are not placeholder values
2. All topics in TOPIC_GROUPS exist in config keywords
3. No duplicate filter terms within a topic
4. start_date format is valid (if set)

Usage:
    python scripts/validate_config.py
    python scripts/validate_config.py --config path/to/config.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

# These topic names are hardcoded in utils/json_tools.py TOPIC_GROUPS
# Keep this in sync with that list (or move TOPIC_GROUPS to config.yaml)
BUILTIN_TOPIC_GROUPS = [
    ["Classification", "Object Detection", "Semantic Segmentation", "Anomaly Detection"],
    ["Object Tracking", "Action Recognition", "Pose Estimation", "Depth Estimation", "Optical Flow"],
    ["Image Generation", "Diffusion Models", "LLM", "Latent Space LLM", "Multimodal"],
    [
        "Scene Understanding", "Video Understanding", "Neural Rendering",
        "Transfer Learning", "Reinforcement Learning", "Graph Neural Networks", "Audio Processing",
    ],
]

PLACEHOLDER_USERNAMES = {"YOUR_GITHUB_USERNAME", "isLinXu", "CHANGE_ME"}
PLACEHOLDER_REPONAMES = {"YOUR_REPO_NAME", "cv-arxiv-daily", "CHANGE_ME"}


def validate_config(config_path: str) -> list[str]:
    warnings: list[str] = []
    errors: list[str] = []

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 1. Check user_name / repo_name
    user_name = config.get("user_name", "")
    repo_name = config.get("repo_name", "")
    if user_name in PLACEHOLDER_USERNAMES:
        errors.append(
            f"[ERROR] config.yaml: user_name='{user_name}' looks like a placeholder. "
            "Please set it to your actual GitHub username."
        )
    if repo_name in PLACEHOLDER_REPONAMES:
        warnings.append(
            f"[WARN]  config.yaml: repo_name='{repo_name}' looks like a placeholder. "
            "Please set it to your actual repository name."
        )

    keywords: dict = config.get("keywords") or {}

    # 2. Check TOPIC_GROUPS topics exist in keywords
    all_grouped = [topic for group in BUILTIN_TOPIC_GROUPS for topic in group]
    for topic in all_grouped:
        if topic not in keywords:
            warnings.append(
                f"[WARN]  TOPIC_GROUPS references topic '{topic}' which is NOT in config.yaml keywords. "
                "It will be silently skipped in GitHub Pages topic lanes."
            )

    # 3. Check for duplicate filters within a topic
    for topic, spec in keywords.items():
        filters = spec.get("filters", []) if isinstance(spec, dict) else []
        seen: set[str] = set()
        for f in filters:
            normalized = f.strip().lower()
            if normalized in seen:
                warnings.append(
                    f"[WARN]  keywords['{topic}']: duplicate filter '{f}' — "
                    "remove one to avoid redundant API queries."
                )
            seen.add(normalized)

    # 4. Check start_date format
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

    # 5. Check max_results sanity
    max_results = config.get("max_results", 100)
    if isinstance(max_results, int) and max_results > 500:
        warnings.append(
            f"[WARN]  config.yaml: max_results={max_results} is very large. "
            "This may cause slow runs and API rate limits. Consider 100-200."
        )

    return errors + warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate paper-list config.yaml")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        sys.exit(1)

    issues = validate_config(str(config_path))

    if not issues:
        print("[OK] Config validation passed — no issues found.")
        sys.exit(0)

    errors = [i for i in issues if i.startswith("[ERROR]")]
    warnings = [i for i in issues if i.startswith("[WARN]")]

    for msg in issues:
        print(msg)

    print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s)")

    if errors:
        print("\nFix errors before running the pipeline.")
        sys.exit(1)
    else:
        print("\nAll errors resolved. Warnings are informational.")
        sys.exit(0)


if __name__ == "__main__":
    main()
