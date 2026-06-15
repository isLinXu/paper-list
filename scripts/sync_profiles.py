#!/usr/bin/env python3
"""Sync profiles from config.yaml to keep them consistent.

Ensures that profiles/full.yaml always matches the current config.yaml
keywords, and that other profiles are valid subsets.

Usage:
    python scripts/sync_profiles.py              # dry-run (preview changes)
    python scripts/sync_profiles.py --apply      # actually write changes
    python scripts/sync_profiles.py --from-config  # sync full.yaml from config.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def sync_full_from_config(config_path: str, apply: bool = False) -> list[str]:
    """Sync profiles/full.yaml from config.yaml keywords.

    Returns list of changes made (or that would be made).
    """
    config = _load_yaml(Path(config_path))
    full_path = PROJECT_ROOT / "profiles" / "full.yaml"
    full = _load_yaml(full_path)

    config_kw = config.get("keywords", {})
    full_kw = full.get("keywords", {})

    changes = []

    # Topics in config but not in full
    new_topics = set(config_kw.keys()) - set(full_kw.keys())
    if new_topics:
        changes.append(f"ADD {len(new_topics)} new topic(s): {sorted(new_topics)}")

    # Topics removed from config
    removed_topics = set(full_kw.keys()) - set(config_kw.keys())
    if removed_topics:
        changes.append(f"REMOVE {len(removed_topics)} topic(s): {sorted(removed_topics)}")

    # Topics with different filters
    for topic in sorted(set(config_kw.keys()) & set(full_kw.keys())):
        c_filters = config_kw[topic].get("filters", []) if isinstance(config_kw[topic], dict) else []
        f_filters = full_kw[topic].get("filters", []) if isinstance(full_kw[topic], dict) else []
        if c_filters != f_filters:
            diff = len(c_filters) - len(f_filters)
            changes.append(f"UPDATE '{topic}': {len(f_filters)} → {len(c_filters)} filters (diff={diff:+d})")

    if not changes:
        print("profiles/full.yaml is already in sync with config.yaml")
        return changes

    print(f"Changes needed for profiles/full.yaml:")
    for c in changes:
        print(f"  {c}")

    if apply:
        # Update full.yaml keywords to match config.yaml
        full["keywords"] = config_kw
        # Also sync other top-level keys that should match
        for key in ("user_name", "repo_name", "max_results", "start_date", "end_date",
                    "base_url", "show_authors", "show_links", "show_badge"):
            if key in config:
                full[key] = config[key]
        _save_yaml(full_path, full)
        print(f"\nApplied: profiles/full.yaml synced from {config_path}")
    else:
        print(f"\nDry-run: use --apply to write changes")

    return changes


def validate_profile_subset(profile_name: str, config_path: str,
                           apply: bool = False) -> list[str]:
    """Validate that a profile's keywords are a subset of config.yaml.

    If apply=True, also removes filters not in config.yaml.
    """
    config = _load_yaml(Path(config_path))
    profile_path = PROJECT_ROOT / "profiles" / f"{profile_name}.yaml"
    profile = _load_yaml(profile_path)

    config_kw = config.get("keywords", {})
    profile_kw = profile.get("keywords", {})

    issues = []

    # Check for topics in profile but not in config
    extra = set(profile_kw.keys()) - set(config_kw.keys())
    if extra:
        issues.append(f"Profile '{profile_name}' has topics not in config: {sorted(extra)}")
        if apply:
            for t in extra:
                del profile_kw[t]

    # Check for filters in profile but not in config
    for topic in sorted(set(profile_kw.keys()) & set(config_kw.keys())):
        p_spec = profile_kw[topic]
        c_spec = config_kw[topic]
        p_filters = p_spec.get("filters", []) if isinstance(p_spec, dict) else []
        c_filters = c_spec.get("filters", []) if isinstance(c_spec, dict) else []

        c_filter_set = set(f.strip().lower() for f in c_filters)
        extra_filters = []
        for f in p_filters:
            if f.strip().lower() not in c_filter_set:
                extra_filters.append(f)

        if extra_filters:
            issues.append(f"  '{topic}' has {len(extra_filters)} filter(s) not in config: {extra_filters[:5]}{'...' if len(extra_filters) > 5 else ''}")
            if apply:
                # Remove filters not in config
                p_spec["filters"] = [f for f in p_filters if f.strip().lower() in c_filter_set]

    if apply and issues:
        profile["keywords"] = profile_kw
        _save_yaml(profile_path, profile)
        issues.insert(0, f"[APPLIED] Fixed profile '{profile_name}'")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync profiles from config.yaml")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--apply", action="store_true", help="Actually write changes")
    parser.add_argument("--from-config", action="store_true",
                        help="Sync profiles/full.yaml from config.yaml")
    parser.add_argument("--validate", action="store_true",
                        help="Validate all profiles are consistent with config")
    args = parser.parse_args()

    if args.from_config:
        changes = sync_full_from_config(args.config, apply=args.apply)
        if changes and not args.apply:
            sys.exit(1)

    if args.validate:
        profiles_dir = PROJECT_ROOT / "profiles"
        all_ok = True
        for pf in sorted(profiles_dir.glob("*.yaml")):
            name = pf.stem
            issues = validate_profile_subset(name, args.config, apply=args.apply)
            if issues:
                print(f"\n[{name}] Issues:")
                for issue in issues:
                    print(f"  {issue}")
                all_ok = False
            else:
                print(f"[{name}] OK")

        if all_ok:
            print("\nAll profiles are consistent with config.yaml")
        else:
            print("\nSome profiles have inconsistencies. Run --from-config --apply to fix.")
            sys.exit(1)


if __name__ == "__main__":
    main()
