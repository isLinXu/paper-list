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
- Guide you through topic customization
- Check your GitHub token setup

**Non-interactive mode** (auto-detect everything from git remote):
```bash
python scripts/setup_fork.py --non-interactive
```

### 2. Validate Your Configuration

```bash
python scripts/validate_config.py
```

This checks for:
- Placeholder values that need changing
- Missing topics in your keyword config
- Duplicate or overlapping filter terms
- Environment variable override validity
- Runtime estimates based on topic count

### 3. Test Locally

```bash
# Fetch papers for the last week
python get_paper.py --start_date 2026-06-01 --end_date 2026-06-08

# Or regenerate from existing data
python regenerate_readme.py
```

---

## Configuration Reference

### config.yaml

| Key | Type | Default | Description |
|:----|:-----|:--------|:------------|
| `user_name` | string | `"YOUR_GITHUB_USERNAME"` | Your GitHub username |
| `repo_name` | string | `"YOUR_REPO_NAME"` | Your repository name |
| `keywords` | dict | *(see below)* | Topic definitions with search filters |
| `topic_groups` | list | *(built-in defaults)* | Homepage layout grouping for topics |
| `max_results` | int | `100` | Max papers per topic per API call |
| `start_date` | string | `null` | Fixed start date (null = last 2 days) |
| `end_date` | string | `null` | Fixed end date (null = today) |
| `publish_readme` | bool | `true` | Generate README.md |
| `publish_gitpage` | bool | `true` | Generate GitHub Pages |
| `publish_wechat` | bool | `false` | Generate WeChat format |
| `show_badge` | bool | `true` | Show GitHub badges |

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

### GitHub Token

A GitHub personal access token increases API rate limits from 10 to 5000 requests/hour.

**Setup:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `public_repo` scope
3. Add as repository secret: Settings → Secrets and variables → Actions → New repository secret
   - Name: `GITHUB_TOKEN`
   - Value: `ghp_xxxxxxxxxxxx`

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

## Troubleshooting

| Problem | Solution |
|:--------|:---------|
| `UnexpectedEmptyPageError` | The arxiv client already retries with smaller page size. Reduce `max_results` if persistent. |
| GitHub API rate limit | Set `GITHUB_TOKEN` environment variable or repository secret. |
| Empty topic in output | Check that the topic name in `keywords` matches exactly (case-sensitive). |
| Topic not in a lane | Add it to `topic_groups` in `config.yaml`. |
| `config.yaml` validation errors | Run `python scripts/validate_config.py` for detailed diagnostics. |
| Pages not updating | Check that GitHub Actions workflows are enabled in the Actions tab. |

---

## Architecture Overview

```
config.yaml ──▶ utils/configs.py ──▶ get_paper.py
                                       │
                    ┌──────────────────┤
                    ▼                  ▼
            utils/get_infos.py   utils/updates.py
            (arXiv API fetch)   (JSON merge + link enrichment)
                    │                  │
                    ▼                  ▼
            docs/data/*.json    (sharded paper store)
                    │
                    ▼
            utils/json_tools.py ──▶ utils/markdown_renderer.py
            (orchestration)        (section-by-section rendering)
                    │
                    ▼
            README.md / docs/index.md / docs/paper_list.md
```

Key design decisions:
- **Sharded JSON storage**: Papers are stored in `docs/data/YYYY-MM.json` shards for efficient incremental updates
- **Config-driven topic groups**: `topic_groups` in `config.yaml` controls homepage layout without code changes
- **Environment variable overrides**: All config keys can be overridden via `PAPER_LIST_*` env vars
- **Incremental rendering**: `selected_topics` parameter limits rendering to only changed topics
