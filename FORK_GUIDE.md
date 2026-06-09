# 🍴 Fork Owner's Guide

This guide helps you customize **your own fork** of paper-list with minimal effort.

## Quick Start (3 Steps)

### 1. Run the Setup Wizard

```bash
python scripts/setup_fork.py
```

The wizard will:
- Auto-detect your GitHub username from git remote
- Set `user_name` and `repo_name` in `config.yaml`
- **Auto-update `docs/_config.yml`** with your fork URLs (no more stale upstream references!)
- **Create `.env` from template** with pre-filled values
- Guide you through profile selection and topic customization
- Check your GitHub token setup

**Non-interactive mode** (auto-detect everything from git remote):
```bash
python scripts/setup_fork.py --non-interactive
```

**Apply a profile directly**:
```bash
python scripts/setup_fork.py --profile minimal
python scripts/setup_fork.py --profile vision
python scripts/setup_fork.py --profile nlp_llm
python scripts/setup_fork.py --profile robotics
python scripts/setup_fork.py --profile full
```

### 2. Run Health Check

```bash
python scripts/health_check.py           # Quick diagnostic
python scripts/health_check.py --verbose # Show all details
python scripts/health_check.py --fix     # Auto-fix where possible
```

This performs a comprehensive pre-flight check:
- ✅ Config validation (delegates to `validate_config.py`)
- ✅ API connectivity (Papers with Code, arXiv, GitHub)
- ✅ Data health (JSON shard integrity, recent activity)
- ✅ Environment readiness (Python, dependencies, .env, git)
- ✅ GitHub Pages readiness (`_config.yml`, Jekyll)

### 3. Test Locally

```bash
# Fetch papers for the last week
python get_paper.py --start_date 2026-06-01 --end_date 2026-06-08

# Or regenerate from existing data
python regenerate_readme.py
```

---

## Makefile Quick Reference

| Command | Description |
|:--------|:------------|
| `make help` | Show all available targets |
| `make dry-run` | Preview what would be fetched |
| `make fetch` | Fetch papers for today |
| `make fetch-week` | Fetch papers for the past week |
| `make fetch-topic TOPIC="Object Detection"` | Fetch a single topic |
| `make validate` | Validate config.yaml |
| `make audit` | Show filter efficiency report |
| `make audit-zombie` | Show only zero-hit (zombie) filters |
| `make setup` | Run the fork setup wizard |
| `make health-check` | One-stop pre-flight diagnostic |
| `make doctor` | Health check with auto-fix |
| `make init-fork` | Non-interactive fork initialization |
| `make serve` | Serve GitHub Pages locally |
| `make regenerate` | Regenerate markdown from existing JSON data |
| `make clean` | Remove generated output files |

---

## Configuration Reference

### config.yaml

| Key | Type | Default | Description |
|:----|:-----|:--------|:------------|
| `user_name` | string | `"YOUR_GITHUB_USERNAME"` | Your GitHub username |
| `repo_name` | string | `"YOUR_REPO_NAME"` | Your repository name |
| `profile` | string | `null` | Preset profile name (minimal/vision/nlp_llm/robotics/full) |
| `keywords` | dict | *(see below)* | Topic definitions with search filters |
| `topic_groups` | list | *(built-in defaults)* | Homepage layout grouping for topics |
| `max_results` | int | `100` | Max papers per topic per API call |
| `start_date` | string | `null` | Fixed start date (null = last 2 days) |
| `end_date` | string | `null` | Fixed end date (null = today) |
| `publish_readme` | bool | `true` | Generate README.md |
| `publish_gitpage` | bool | `true` | Generate GitHub Pages |
| `publish_wechat` | bool | `false` | Generate WeChat format |
| `show_badge` | bool | `true` | Show GitHub badges |
| `concurrent_fetch` | bool | `true` | Enable parallel topic fetching |
| `max_workers` | int | `3` | Number of concurrent fetch threads |
| `deduplicate` | bool | `true` | Deduplicate cross-topic papers |

### Profiles

Profiles are pre-built configurations stored in `profiles/`. They let you start quickly:

| Profile | Topics | Best For |
|:--------|:-------|:---------|
| `minimal` | 3 core topics | Beginners, quick evaluation |
| `vision` | 12 CV topics | Computer vision researchers |
| `nlp_llm` | 8 NLP/LLM topics | NLP researchers |
| `robotics` | 9 robotics topics | Robotics researchers |
| `full` | 20+ topics | General AI research tracking |

**How profiles work:**
1. Set `profile: vision` in `config.yaml` (or use `--profile vision` flag)
2. The profile is loaded as the **base** configuration
3. Your `config.yaml` values **override** the profile (you can add/remove topics)
4. Keywords are deep-merged: your additions win over the profile

### Environment Variable Overrides

Every config key can be overridden via environment variables, which is useful for CI/CD:

| Environment Variable | Config Key | Example |
|:--------------------|:-----------|:--------|
| `PAPER_LIST_USER` | `user_name` | `export PAPER_LIST_USER=myname` |
| `PAPER_LIST_REPO` | `repo_name` | `export PAPER_LIST_REPO=my-papers` |
| `PAPER_LIST_MAX_RESULTS` | `max_results` | `export PAPER_LIST_MAX_RESULTS=50` |
| `PAPER_LIST_PUBLISH_README` | `publish_readme` | `export PAPER_LIST_PUBLISH_README=true` |
| `PAPER_LIST_PUBLISH_GITPAGE` | `publish_gitpage` | `export PAPER_LIST_PUBLISH_GITPAGE=true` |
| `PAPER_LIST_SHOW_BADGE` | `show_badge` | `export PAPER_LIST_SHOW_BADGE=false` |
| `PAPER_LIST_START_DATE` | `start_date` | `export PAPER_LIST_START_DATE=2026-01-01` |
| `PAPER_LIST_END_DATE` | `end_date` | `export PAPER_LIST_END_DATE=2026-06-01` |

Environment variables take **precedence** over `config.yaml` values.

### .env File

You can also set environment variables in a `.env` file at the project root:

```bash
# Copy the template and fill in your values
cp .env.example .env
```

The `.env` file is **automatically loaded** by `utils/configs.py` — no need to manually `export` variables. This works for both local runs and CI/CD.

> **Note**: Existing environment variables always take precedence over `.env` values (standard dotenv convention).

### GitHub Token

A GitHub personal access token increases API rate limits from 10 to 5000 requests/hour.

**Setup:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `public_repo` scope
3. Add as repository secret: Settings → Secrets and variables → Actions → New repository secret
   - Name: `GITHUB_TOKEN`
   - Value: `ghp_xxxxxxxxxxxx`
4. Or add to your `.env` file: `GITHUB_TOKEN=ghp_xxxxxxxxxxxx`

---

## Customizing Topics

### Adding a New Topic

Add it to `config.yaml` under `keywords`:

```yaml
keywords:
  # ... existing topics ...
  "Medical Imaging":
    filters: ["Medical Image", "Clinical Imaging", "Radiology AI"]
```

### Temporarily Disabling a Topic

Instead of removing a topic, you can disable it:

```yaml
keywords:
  "Object Detection":
    enabled: false           # ← skip this topic
    filters: ["Object Detection", "2D Object Detection"]
```

Disabled topics are excluded from fetching and rendering, but preserved for easy re-enabling.

### Adding a Topic to a Lane (Homepage Group)

Add the topic name to the appropriate group in `config.yaml` under `topic_groups`:

```yaml
topic_groups:
  - ["Perception Core", "Vision Systems", "theme-card--vision",
     ["Classification", "Object Detection", "Semantic Segmentation",
      "Anomaly Detection", "Medical Imaging"]]   # <-- added here
```

Or create a new lane:

```yaml
topic_groups:
  # ... existing groups ...
  - ["Life Sciences", "Medical AI", "theme-card--medical",
     ["Medical Imaging", "AI for Science"]]
```

Available CSS classes for cards:
- `theme-card--vision` (blue)
- `theme-card--motion` (green)
- `theme-card--foundation` (purple)
- `theme-card--systems` (orange)
- Or define your own in `docs/assets/css/`

### Removing a Topic

1. Remove it from `keywords` in `config.yaml`
2. Remove it from any `topic_groups` entry that references it
3. Run `python scripts/validate_config.py` to verify

---

## GitHub Actions Workflows

After forking, you need to **manually enable** the workflows:

1. Go to your fork's **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. For each workflow, click **"Enable workflow"**

### Workflow Schedule

| Workflow | Schedule | Purpose |
|:---------|:---------|:--------|
| `Run Arxiv Papers Daily` | Every 8 hours | Fetch new papers and update README + Pages |
| `Run Update Paper Links Weekly` | Weekly (Monday) | Enrich existing papers with code links |

### Manual Trigger

You can also trigger workflows manually from the Actions tab using "Run workflow".

---

## Common Customization Patterns

### Pattern 1: Minimal Fork (Track 3-5 Topics Only)

```bash
# Apply the minimal profile
python scripts/setup_fork.py --profile minimal
```

Or manually:

```yaml
# config.yaml
user_name: "your-username"
repo_name: "your-paper-list"
max_results: 50
keywords:
  "Object Detection":
    filters: ["Object Detection", "2D Object Detection"]
  "Diffusion Models":
    filters: ["Diffusion Model", "Stable Diffusion"]
  "LLM":
    filters: ["Large Language Model", "LLM"]
topic_groups:
  - ["Core Research", "My Topics", "theme-card--foundation",
     ["Object Detection", "Diffusion Models", "LLM"]]
```

### Pattern 2: Research Group Fork (Niche Topics)

```yaml
keywords:
  "3D Gaussian Splatting":
    filters: ["3D Gaussian Splatting", "Gaussian Splatting"]
  "NeRF":
    filters: ["Neural Radiance Fields", "NeRF"]
  "Neural Rendering":
    filters: ["Neural Rendering", "Novel View Synthesis"]
topic_groups:
  - ["3D Vision", "Rendering & Reconstruction", "theme-card--motion",
     ["3D Gaussian Splatting", "NeRF", "Neural Rendering"]]
```

### Pattern 3: Chinese Research Community

```yaml
publish_wechat: true
json_wechat_path: "docs/data/wechat"
md_wechat_path: "docs/wechat.md"
```

---

## Diagnostic Tools

### validate_config.py — Configuration Validation

```bash
python scripts/validate_config.py              # Basic validation
python scripts/validate_config.py --verbose    # Show all checks
```

Checks performed:
- Placeholder values that need changing
- Missing topics in keyword config
- Duplicate or overlapping filter terms
- Zombie filters (zero hits in recent data)
- `docs/_config.yml` stale upstream references
- `.env` file existence
- Profile consistency
- Concurrent fetch configuration
- Publish channel sanity (at least one enabled)
- Environment variable override validity
- Runtime estimates based on topic count

### health_check.py — One-Stop Diagnostic

```bash
python scripts/health_check.py           # Quick check
python scripts/health_check.py --verbose # Detailed output
python scripts/health_check.py --fix     # Auto-fix where possible
```

Checks performed:
1. **Configuration** — validates config.yaml (delegates to validate_config.py)
2. **API Connectivity** — tests Papers with Code, arXiv, GitHub APIs
3. **Data Health** — JSON shard integrity, paper counts, recency
4. **Environment** — Python version, dependencies, .env, git remote
5. **GitHub Pages** — `_config.yml` freshness, Gemfile presence

### filter_audit.py — Filter Efficiency Report

```bash
python scripts/filter_audit.py              # Full report
python scripts/filter_audit.py --zombie      # Only zero-hit filters
```

---

## Troubleshooting

| Problem | Solution |
|:--------|:---------|
| `UnexpectedEmptyPageError` | The arxiv client already retries with smaller page size. Reduce `max_results` if persistent. |
| GitHub API rate limit | Set `GITHUB_TOKEN` in `.env` or as repository secret. |
| Empty topic in output | Check that the topic name in `keywords` matches exactly (case-sensitive). |
| Topic not in a lane | Add it to `topic_groups` in `config.yaml`. |
| `config.yaml` validation errors | Run `python scripts/validate_config.py` for detailed diagnostics. |
| Pages not updating | Check that GitHub Actions workflows are enabled in the Actions tab. |
| `docs/_config.yml` still points to upstream | Run `python scripts/setup_fork.py` or `make doctor` to auto-fix. |
| Missing Python packages | Run `pip install -r requirements.txt`. |
| No recent data | Pipeline may not be running — check GitHub Actions. |

---

## Architecture Overview

```
config.yaml ──▶ utils/configs.py ──▶ get_paper.py
     │               │                   │
     │               │                   ├── utils/concurrent_fetch.py (parallel)
     │               │                   ├── utils/get_infos.py (arXiv API)
     │               │                   └── utils/updates.py (JSON merge)
     │               │                       │
.env ───────────────┤                       ▼
                     │               docs/data/*.json (sharded store)
     profiles/ ─────┤                       │
                     │                       ▼
                     └─────── utils/json_tools.py ──▶ utils/markdown_renderer.py
                                                     (section-by-section rendering)
                                                             │
                                                             ▼
                                                     README.md / docs/index.md / docs/paper_list.md
```

Key design decisions:
- **Sharded JSON storage**: Papers are stored in `docs/data/YYYY-MM.json` shards for efficient incremental updates
- **Config-driven topic groups**: `topic_groups` in `config.yaml` controls homepage layout without code changes
- **Environment variable overrides**: All config keys can be overridden via `PAPER_LIST_*` env vars
- **Automatic .env loading**: No manual exports needed — `utils/configs.py` loads `.env` automatically
- **Profile layering**: Profiles provide a base config; your `config.yaml` overrides selectively
- **Incremental rendering**: `selected_topics` parameter limits rendering to only changed topics
- **Concurrent fetching**: Multi-threaded API calls with rate limiting and cross-topic deduplication
