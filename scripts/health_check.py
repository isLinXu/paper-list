#!/usr/bin/env python3
"""One-stop pre-flight health check for paper-list.

Runs a comprehensive diagnostic covering:
1. Config validation (delegates to validate_config.py)
2. API connectivity (Papers with Code, arXiv, GitHub)
3. Data health (JSON shard integrity, recent activity)
4. Environment readiness (Python, dependencies, .env, git)
5. GitHub Pages readiness (_config.yml, Jekyll)

Exit codes:
  0 — all checks passed (warnings allowed)
  1 — one or more errors found
  2 — critical failure (cannot run checks)

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --verbose     # show all details
    python scripts/health_check.py --fix         # attempt auto-fix where possible
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml


# ── Helpers ──────────────────────────────────────────────────────────

class HealthReport:
    """Accumulates check results."""

    def __init__(self):
        self.passed = []
        self.warnings = []
        self.errors = []
        self.infos = []

    def ok(self, msg: str):
        self.passed.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def err(self, msg: str):
        self.errors.append(msg)

    def info(self, msg: str):
        self.infos.append(msg)

    def summary(self) -> str:
        lines = []
        lines.append(f"  Passed:   {len(self.passed)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        lines.append(f"  Errors:   {len(self.errors)}")
        lines.append(f"  Info:     {len(self.infos)}")
        return "\n".join(lines)

    def has_errors(self) -> bool:
        return len(self.errors) > 0


def _http_reachable(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Check if a URL is reachable. Returns (success, message)."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "paper-list-health-check/1.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return True, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)[:100]


# ── Check Functions ──────────────────────────────────────────────────

def check_config(report: HealthReport, config_path: str, fix: bool = False) -> dict | None:
    """Load and validate config.yaml."""
    config_file = Path(config_path)
    if not config_file.exists():
        report.err(f"config.yaml not found at {config_file}")
        return None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        report.err(f"config.yaml parse error: {e}")
        return None

    report.ok("config.yaml parses correctly")

    # Delegate deeper validation to validate_config.py
    try:
        from scripts.validate_config import validate_config
        issues = validate_config(config_path)
        errs = [i for i in issues if i.startswith("[ERROR]")]
        warns = [i for i in issues if i.startswith("[WARN]")]
        infos = [i for i in issues if i.startswith("[INFO]")]
        for e in errs:
            report.err(e.replace("[ERROR] ", ""))
        for w in warns:
            report.warn(w.replace("[WARN]  ", ""))
        for i in infos:
            report.info(i.replace("[INFO] ", ""))
        if not errs:
            report.ok("config.yaml validation passed")
    except ImportError:
        report.warn("Could not import validate_config module — skipping deep validation")

    return config


def check_api_connectivity(report: HealthReport, config: dict | None):
    """Check if required APIs are reachable."""
    print("\n  Checking API connectivity...")

    # Papers with Code API
    base_url = (config or {}).get("base_url", "https://arxiv.paperswithcode.com/api/v0/papers/")
    ok, msg = _http_reachable(base_url + "?q=test&page=1", timeout=15)
    if ok:
        report.ok(f"Papers with Code API reachable ({msg})")
    else:
        report.err(f"Papers with Code API unreachable: {msg}")

    # arXiv
    ok, msg = _http_reachable("https://arxiv.org/", timeout=10)
    if ok:
        report.ok(f"arXiv reachable ({msg})")
    else:
        report.warn(f"arXiv unreachable: {msg} (may be temporary)")

    # GitHub API
    ok, msg = _http_reachable("https://api.github.com/", timeout=10)
    if ok:
        report.ok(f"GitHub API reachable ({msg})")
    else:
        report.warn(f"GitHub API unreachable: {msg}")


def check_data_health(report: HealthReport, config: dict | None):
    """Check JSON data shard integrity and recent activity."""
    print("\n  Checking data health...")

    json_dir = Path((config or {}).get("json_readme_path", "./docs/data"))
    if not json_dir.is_absolute():
        json_dir = PROJECT_ROOT / json_dir

    if not json_dir.exists():
        report.warn(f"Data directory {json_dir} does not exist yet (first run?)")
        return

    # Scan shard files
    shard_files = sorted(json_dir.glob("*.json"))
    if not shard_files:
        report.warn("No JSON data files found. Run get_paper.py first.")
        return

    report.ok(f"Found {len(shard_files)} JSON data shard(s)")

    # Check integrity of each shard
    corrupted = 0
    total_papers = 0
    topics_found = set()
    newest_date = None

    for sf in shard_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
            for topic, papers in data.items():
                if isinstance(papers, dict):
                    total_papers += len(papers)
                    topics_found.add(topic)
        except (json.JSONDecodeError, UnicodeDecodeError):
            corrupted += 1

    if corrupted:
        report.err(f"{corrupted} corrupted JSON shard(s) found")
    else:
        report.ok("All JSON shards are valid")

    report.info(f"Total papers indexed: {total_papers} across {len(topics_found)} topics")

    # Check recency
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=7)
    recent_shards = [
        sf for sf in shard_files
        if sf.stem >= recent_cutoff.strftime("%Y-%m")
    ]
    if recent_shards:
        report.ok(f"Recent data found (last 7 days): {[sf.name for sf in recent_shards]}")
    else:
        report.warn(
            "No recent data shards found (last 7 days). "
            "The pipeline may not be running. Check GitHub Actions."
        )


def check_environment(report: HealthReport, fix: bool = False):
    """Check Python version, dependencies, .env, and git."""
    print("\n  Checking environment...")

    # Python version
    py_version = sys.version_info
    if py_version >= (3, 10):
        report.ok(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        report.err(f"Python {py_version.major}.{py_version.minor} — requires 3.10+")

    # Required packages
    required = {"yaml": "pyyaml", "arxiv": "arxiv", "requests": "requests", "matplotlib": "matplotlib"}
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        report.err(f"Missing Python packages: {', '.join(missing)}. Run: pip install -r requirements.txt")
    else:
        report.ok("All required Python packages installed")

    # .env file
    dot_env = PROJECT_ROOT / ".env"
    dot_env_example = PROJECT_ROOT / ".env.example"
    if dot_env.exists():
        report.ok(".env file exists")
    elif dot_env_example.exists():
        report.warn(".env file not found. Create one: cp .env.example .env")
    else:
        report.info(".env.example not found (may be intentional)")

    # GITHUB_TOKEN
    token_found = bool(os.environ.get("GITHUB_TOKEN"))
    if not token_found and dot_env.exists():
        for line in dot_env.read_text().splitlines():
            if line.strip().startswith("GITHUB_TOKEN="):
                val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    token_found = True
                    break
    if token_found:
        report.ok("GITHUB_TOKEN is configured")
    else:
        report.warn("GITHUB_TOKEN not set — API rate limits will be restricted (10 req/hr)")

    # Git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            report.ok(f"Git remote: {result.stdout.strip()}")
        else:
            report.warn("No git remote configured")
    except Exception:
        report.warn("Cannot detect git remote")


def check_github_pages(report: HealthReport, config: dict | None, fix: bool = False):
    """Check GitHub Pages readiness."""
    print("\n  Checking GitHub Pages readiness...")

    jekyll_config = PROJECT_ROOT / "docs" / "_config.yml"
    if not jekyll_config.exists():
        report.warn("docs/_config.yml not found — GitHub Pages won't work")
        return

    report.ok("docs/_config.yml exists")

    content = jekyll_config.read_text(encoding="utf-8")

    # Check for stale upstream references
    if "isLinXu" in content:
        report.err(
            "docs/_config.yml still references upstream owner 'isLinXu'. "
            "Run 'python scripts/setup_fork.py' to auto-fix."
        )
        if fix:
            import re
            user_name = (config or {}).get("user_name", "")
            repo_name = (config or {}).get("repo_name", "paper-list")
            if user_name and user_name not in ("isLinXu", "CHANGE_ME"):
                content = content.replace("isLinXu/paper-list", f"{user_name}/{repo_name}")
                content = re.sub(r'(^\s+github:\s*)isLinXu', rf'\1{user_name}', content, flags=re.MULTILINE)
                content = re.sub(r'(^\s+name:\s*)"isLinXu"', rf'\1"{user_name}"', content, flags=re.MULTILINE)
                jekyll_config.write_text(content, encoding="utf-8")
                report.ok("Auto-fixed docs/_config.yml URLs")
    else:
        report.ok("docs/_config.yml has no stale upstream references")

    # Check Gemfile
    gemfile = PROJECT_ROOT / "Gemfile"
    if gemfile.exists():
        report.ok("Gemfile exists (Jekyll dependencies)")
    else:
        report.warn("Gemfile not found — local Jekyll preview won't work")


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Paper-List health check")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all details")
    parser.add_argument("--fix", action="store_true", help="Attempt auto-fix where possible")
    args = parser.parse_args()

    report = HealthReport()

    print("=" * 60)
    print("  Paper-List Health Check")
    print("=" * 60)

    # 1. Config
    print("\n  Checking configuration...")
    config = check_config(report, args.config, fix=args.fix)

    # 2. API connectivity
    check_api_connectivity(report, config)

    # 3. Data health
    check_data_health(report, config)

    # 4. Environment
    check_environment(report, fix=args.fix)

    # 5. GitHub Pages
    check_github_pages(report, config, fix=args.fix)

    # Print results
    print("\n" + "=" * 60)
    print("  Results")
    print("=" * 60)

    if report.passed:
        if args.verbose:
            for msg in report.passed:
                print(f"  [PASS]  {msg}")
        else:
            print(f"\n  [PASS]  {len(report.passed)} check(s) passed (use --verbose for details)")

    if report.infos:
        print()
        for msg in report.infos:
            print(f"  [INFO]  {msg}")

    if report.warnings:
        print()
        for msg in report.warnings:
            print(f"  [WARN]  {msg}")

    if report.errors:
        print()
        for msg in report.errors:
            print(f"  [FAIL]  {msg}")

    print(f"\n{report.summary()}")
    print("=" * 60)

    if report.has_errors():
        print("\n  Fix the errors above before running the pipeline.")
        sys.exit(1)
    elif report.warnings:
        print("\n  No blocking errors. Address warnings when convenient.")
        sys.exit(0)
    else:
        print("\n  All checks passed! Your fork is ready to go.")
        sys.exit(0)


if __name__ == "__main__":
    main()
