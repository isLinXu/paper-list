#!/usr/bin/env python3
"""Interactive fork setup wizard for paper-list.

Guides fork owners through the minimal configuration changes
needed to get their own paper-list running.

Enhanced features:
- Profile selection (minimal / vision / nlp_llm / robotics / full)
- Automatic badge/URL replacement
- Dry-run verification step

Usage:
    python scripts/setup_fork.py
    python scripts/setup_fork.py --non-interactive   # auto-detect from git remote
    python scripts/setup_fork.py --profile minimal    # apply a profile directly
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROFILES_DIR = PROJECT_ROOT / "profiles"

AVAILABLE_PROFILES = {
    "minimal": "3 core topics (Object Detection, LLM, Diffusion Models)",
    "vision": "Full CV suite (12 topics)",
    "nlp_llm": "NLP/LLM direction (8 topics)",
    "robotics": "Robotics & autonomous driving (9 topics)",
    "full": "All 20+ topics (current default)",
}


def _git_remote_info() -> tuple[str, str]:
    """Try to extract username and repo from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            return "", ""
        url = result.stdout.strip()
        match = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$", url)
        if match:
            return match.group(1), match.group(2)
    except Exception:
        pass
    return "", ""


def _detect_env_token() -> bool:
    """Check if GITHUB_TOKEN is set in environment."""
    return bool(os.environ.get("GITHUB_TOKEN"))


def _read_config() -> str:
    return CONFIG_PATH.read_text(encoding="utf-8")


def _write_config(content: str) -> None:
    CONFIG_PATH.write_text(content, encoding="utf-8")


def _update_yaml_value(content: str, key: str, old_val: str, new_val: str) -> str:
    """Replace a YAML key's quoted value in the config text."""
    pattern = rf'({key}:\s*)"{re.escape(old_val)}"'
    replacement = rf'\1"{new_val}"'
    new_content, count = re.subn(pattern, replacement, content)
    if count == 0:
        pattern = rf'({key}:\s*){re.escape(old_val)}(\s|$)'
        replacement = rf'\1{new_val}\2'
        new_content, count = re.subn(pattern, replacement, content)
    return new_content


def _apply_profile(profile_name: str) -> None:
    """Copy a profile file over config.yaml."""
    profile_path = PROFILES_DIR / f"{profile_name}.yaml"
    if not profile_path.exists():
        print(f"[ERROR] Profile '{profile_name}' not found at {profile_path}")
        sys.exit(1)
    shutil.copy2(profile_path, CONFIG_PATH)
    print(f"  Applied profile '{profile_name}' to config.yaml")


def _replace_hardcoded_urls(content: str, user_name: str, repo_name: str) -> str:
    """Replace all hardcoded isLinXu/paper-list references in config.yaml."""
    # Replace in user_name / repo_name fields
    content = _update_yaml_value(content, "user_name",
                                  re.search(r'user_name:\s*"([^"]*)"', content).group(1) if re.search(r'user_name:\s*"([^"]*)"', content) else "",
                                  user_name)
    content = _update_yaml_value(content, "repo_name",
                                  re.search(r'repo_name:\s*"([^"]*)"', content).group(1) if re.search(r'repo_name:\s*"([^"]*)"', content) else "",
                                  repo_name)
    return content


def run_interactive(git_user: str, git_repo: str) -> None:
    """Run the interactive setup wizard."""
    print("=" * 60)
    print("  Paper-List Fork Setup Wizard")
    print("=" * 60)
    print()
    print("This wizard will help you configure your fork with the")
    print("minimum changes needed to get it running.\n")

    content = _read_config()

    # --- Step 1: Profile selection ---
    print("Step 1: Choose a Profile")
    print("   Profiles are pre-built configurations with curated topic sets.")
    print()
    for name, desc in AVAILABLE_PROFILES.items():
        marker = " (recommended for beginners)" if name == "minimal" else ""
        print(f"   [{name:>10}] {desc}{marker}")
    print()

    current_profile_hint = "full"
    profile_input = input(f"   Choose a profile [{current_profile_hint}]: ").strip().lower()
    profile_name = profile_input if profile_input in AVAILABLE_PROFILES else current_profile_hint

    if profile_name != "full":
        _apply_profile(profile_name)
        content = _read_config()
        print(f"   Applied profile: {profile_name}\n")
    else:
        print("   Keeping full configuration.\n")

    # --- Step 2: GitHub username ---
    current_user = re.search(r'user_name:\s*"([^"]*)"', content)
    current_user = current_user.group(1) if current_user else ""
    default_user = git_user or current_user

    print(f"Step 2: GitHub Username")
    print(f"   Current value: {current_user or '(not set)'}")
    if git_user:
        print(f"   Auto-detected from git remote: {git_user}")
    user_input = input(f"   Enter your GitHub username [{default_user}]: ").strip()
    user_name = user_input or default_user
    if user_name and user_name not in ("YOUR_GITHUB_USERNAME", "CHANGE_ME"):
        content = _update_yaml_value(content, "user_name", current_user, user_name)
        print(f"   Set user_name = {user_name}\n")
    else:
        print("   Skipped - you must set user_name manually in config.yaml\n")

    # --- Step 3: Repo name ---
    current_repo = re.search(r'repo_name:\s*"([^"]*)"', content)
    current_repo = current_repo.group(1) if current_repo else ""
    default_repo = git_repo or current_repo or "paper-list"

    print(f"Step 3: Repository Name")
    print(f"   Current value: {current_repo or '(not set)'}")
    if git_repo:
        print(f"   Auto-detected from git remote: {git_repo}")
    user_input = input(f"   Enter your repo name [{default_repo}]: ").strip()
    repo_name = user_input or default_repo
    if repo_name:
        content = _update_yaml_value(content, "repo_name", current_repo, repo_name)
        print(f"   Set repo_name = {repo_name}\n")

    # --- Step 4: Research topics customization ---
    print("Step 4: Research Topics")
    print("   Your config.yaml now has keywords defined.")
    print("   Tips:")
    print("     - Set 'enabled: false' to temporarily disable a topic")
    print("     - Remove topics you don't care about entirely")
    print("     - Reduce max_results for faster initial runs")
    customize = input("   Open config.yaml for editing now? [y/N]: ").strip().lower()
    if customize in ("y", "yes"):
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
        os.system(f"{editor} {CONFIG_PATH}")
        content = _read_config()
    print()

    # --- Step 5: GitHub Token ---
    has_token = _detect_env_token()
    print("Step 5: GitHub Token (optional but recommended)")
    print("   A GitHub token increases API rate limits from 10 to 5000 req/hour.")
    if has_token:
        print("   GITHUB_TOKEN is already set in your environment.")
    else:
        print("   To set it up:")
        print("   1. Go to GitHub Settings > Developer settings > Personal access tokens")
        print("   2. Generate a token with 'public_repo' scope")
        print("   3. Add it as a repository secret: Settings > Secrets > New secret")
        print("      Name: GITHUB_TOKEN  Value: ghp_xxxxx")
    print()

    # --- Step 6: Enable workflows ---
    print("Step 6: Enable GitHub Actions Workflows")
    print("   After pushing to your fork, go to the Actions tab and click")
    print("   'Enable workflow' for both workflows:")
    print("     - Run Arxiv Papers Daily")
    print("     - Run Update Paper Links Weekly")
    print()

    # --- Step 7: Dry-run verification ---
    print("Step 7: Verify Configuration")
    verify = input("   Run a dry-run to verify your config? [Y/n]: ").strip().lower()
    if verify not in ("n", "no"):
        print()
        os.system(f"cd {PROJECT_ROOT} && python get_paper.py --dry-run --start_date 2026-06-01 --end_date 2026-06-08")
    print()

    # --- Save ---
    _write_config(content)
    print("=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review config:       cat config.yaml")
    print("  2. Validate config:    python scripts/validate_config.py")
    print("  3. Test locally:       python get_paper.py --start_date 2026-06-01 --end_date 2026-06-08")
    print("  4. Push and enable:    git push origin main")
    print()


def run_non_interactive() -> None:
    """Auto-configure from git remote without user input."""
    git_user, git_repo = _git_remote_info()
    if not git_user:
        print("[ERROR] Cannot auto-detect GitHub username from git remote.")
        print("        Run with --interactive or set user_name manually in config.yaml")
        sys.exit(1)

    content = _read_config()
    current_user = re.search(r'user_name:\s*"([^"]*)"', content)
    current_user = current_user.group(1) if current_user else ""
    current_repo = re.search(r'repo_name:\s*"([^"]*)"', content)
    current_repo = current_repo.group(1) if current_repo else ""

    content = _update_yaml_value(content, "user_name", current_user, git_user)
    if git_repo:
        content = _update_yaml_value(content, "repo_name", current_repo, git_repo)

    _write_config(content)
    print(f"Auto-configured: user_name={git_user}, repo_name={git_repo or current_repo}")
    print("   Run 'python scripts/validate_config.py' to verify.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper-List fork setup wizard")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Auto-detect settings from git remote (no prompts)")
    parser.add_argument("--profile", type=str, default=None,
                        choices=list(AVAILABLE_PROFILES.keys()),
                        help="Apply a preset profile directly (non-interactive)")
    args = parser.parse_args()

    if not CONFIG_PATH.exists():
        print(f"[ERROR] config.yaml not found at {CONFIG_PATH}")
        print("        Make sure you're running this from the project root.")
        sys.exit(1)

    if args.profile:
        _apply_profile(args.profile)
        git_user, git_repo = _git_remote_info()
        if git_user:
            content = _read_config()
            current_user = re.search(r'user_name:\s*"([^"]*)"', content)
            current_user = current_user.group(1) if current_user else ""
            content = _update_yaml_value(content, "user_name", current_user, git_user)
            _write_config(content)
            print(f"Auto-set user_name={git_user}")
        print(f"Profile '{args.profile}' applied. Run 'python scripts/validate_config.py' to verify.")
        return

    if args.non_interactive:
        run_non_interactive()
    else:
        git_user, git_repo = _git_remote_info()
        run_interactive(git_user, git_repo)


if __name__ == "__main__":
    main()
