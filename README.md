![paper-list](https://github.com/isLinXu/issues/assets/59380685/dbd27f25-e7d7-4a0f-bdc2-d9b06fc03a2e)![GitHub stars](https://img.shields.io/github/stars/isLinXu/paper-list)![GitHub forks](https://img.shields.io/github/forks/isLinXu/paper-list)![GitHub watchers](https://img.shields.io/github/watchers/isLinXu/paper-list)[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fatrox%2Fsync-dotenv%2Fbadge&style=flat)](https://github.com/isLinXu/paper-list)![img](https://badgen.net/badge/icon/learning?icon=deepscan&label)![GitHub repo size](https://img.shields.io/github/repo-size/isLinXu/paper-list.svg?style=flat-square)![GitHub language count](https://img.shields.io/github/languages/count/isLinXu/paper-list)![GitHub last commit](https://img.shields.io/github/last-commit/isLinXu/paper-list)![GitHub](https://img.shields.io/github/license/isLinXu/paper-list.svg?style=flat-square)![img](https://hits.dwyl.com/isLinXu/paper-list.svg)<p align="center"><h1 align="center"><br><ins>Paper-List-DAILY</ins><br>Automatically Update Papers Daily in list</h1></p>
## Updated on 2026.04.12

![paper_list](https://github.com/isLinXu/issues/assets/59380685/0ab31126-9ef4-4c49-bf80-8dae2a3acaa8)

## Introduction

This repository provides a daily-updated list of computer vision papers from arXiv, organized by topic. The updates are automated using GitHub Actions to ensure you stay current with the latest research.

Online documentation: [https://islinxu.github.io/paper-list/](https://islinxu.github.io/paper-list/)

## PapersWithCode Archive Ingest

This repository now includes a structured ingestion lane for archived PapersWithCode pages.
Instead of storing scraped results as loose Markdown, the archive workflow keeps:

- raw archived HTML and discovery manifests
- normalized paper records with provenance
- enrichment-ready fields such as repo languages, frameworks, and architecture labels
- generated docs under `docs/pwc/`

The repository now ships both:

- `sample.json`: a schema example for development
- `sample_live.json`: a real-world seed record for live OpenAlex and GitHub validation

Recommended entry points:

```bash
python scripts/pwc_discover.py --input-html data/pwc_archive/raw/home.html --source-url https://web.archive.org/web/20250616051252/https://paperswithcode.com/
python scripts/pwc_cdx_discover.py --from-timestamp 20250101 --to-timestamp 20250630
python scripts/pwc_seed_from_archive.py --archive-url https://web.archive.org/web/20250616051252/https://paperswithcode.com/ --archive-url https://web.archive.org/web/20250616051252/https://paperswithcode.com/sota --limit 20
python scripts/pwc_fetch_archive.py --entity-type paper --limit 10
python scripts/pwc_parse_pages.py --input-html data/pwc_archive/raw/example-paper.html --archive-url https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/example-diffusion-transformer
python scripts/pwc_enrich_openalex.py --mailto your-email@example.com
python scripts/pwc_enrich_github.py
python scripts/pwc_build_catalog.py
```

GitHub enrichment works best with a personal access token because unauthenticated API calls can hit rate limits quickly during batch runs:

```bash
export GITHUB_TOKEN=your_token_here
python scripts/pwc_enrich_github.py --input data/pwc_archive/normalized/papers
```

If GitHub enrichment reports rate limiting, keep the current normalized files, set `GITHUB_TOKEN`, and rerun only the GitHub step before rebuilding the catalog.

Or run a small end-to-end batch:

```bash
python scripts/pwc_run_pipeline.py --from-timestamp 20250101 --to-timestamp 20250630 --limit 5 --mailto your-email@example.com
```

If CDX is slow, bootstrap directly from archived entry pages:

```bash
python scripts/pwc_run_pipeline.py --seed-archive-url https://web.archive.org/web/20250616051252/https://paperswithcode.com/ --seed-archive-url https://web.archive.org/web/20250616051252/https://paperswithcode.com/sota --limit 5
```

To resume after partial success, reuse local checkpoint files:

```bash
python scripts/pwc_run_pipeline.py --reuse-existing-manifest --reuse-existing-fetch-state --skip-openalex --skip-github
```

To avoid real-time Archive dependence, merge local seed sources and manual URLs:

```bash
python scripts/pwc_merge_seed_sources.py --manifest data/pwc_archive/staging/seed_manifest.json --manifest data/pwc_archive/staging/discovery_manifest.json
python scripts/pwc_run_pipeline.py --use-local-seeds --limit 5
```

For resumable archive fetches across larger seed pools, use the bulk sync worker:

```bash
python scripts/pwc_bulk_sync.py --batch-size 5
python scripts/pwc_bulk_sync.py --batch-size 5 --max-batches 4 --wait-between-batches 30
```

This worker writes live progress to:

- `data/pwc_archive/staging/fetch_state.json`
- `data/pwc_archive/staging/bulk_sync_state.json`

If Wayback responds with `429` errors, keep the current state files and rerun later; the worker will respect cooldown windows and continue from the remaining eligible queue.

Catalog page: [docs/pwc/index.md](docs/pwc/index.md)

## Analytics

- Dashboard: [docs/analytics/](docs/analytics/)

![trend_daily](docs/analytics/charts/trend_daily.png)

![topic_rank](docs/analytics/charts/topic_rank.png)

![code_coverage](docs/analytics/charts/code_coverage_trend.png)

![top_authors](docs/analytics/charts/top_authors.png)

## Usage

To generate the paper list locally, follow these steps:

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Script**
   ```bash
   python get_paper.py
   ```

3. **Configuration**
   You can customize the search keywords and other settings in `config.yaml`.

### Advanced Usage

You can also use the scripts in the `scripts/` directory for additional tasks:

- **Count Papers in Range**: Count the number of papers within a specific date range.
  ```bash
  python scripts/count_range.py 2024-01-01 2024-12-31
  ```

## Paper List

  <ol>
    <li><a href=docs/Classification.md>Classification</a></li>
    <li><a href=docs/Object_Detection.md>Object Detection</a></li>
    <li><a href=docs/Semantic_Segmentation.md>Semantic Segmentation</a></li>
    <li><a href=docs/Object_Tracking.md>Object Tracking</a></li>
    <li><a href=docs/Action_Recognition.md>Action Recognition</a></li>
    <li><a href=docs/Pose_Estimation.md>Pose Estimation</a></li>
    <li><a href=docs/Image_Generation.md>Image Generation</a></li>
    <li><a href=docs/LLM.md>LLM</a></li>
    <li><a href=docs/Scene_Understanding.md>Scene Understanding</a></li>
    <li><a href=docs/Depth_Estimation.md>Depth Estimation</a></li>
    <li><a href=docs/Audio_Processing.md>Audio Processing</a></li>
    <li><a href=docs/Multimodal.md>Multimodal</a></li>
    <li><a href=docs/Anomaly_Detection.md>Anomaly Detection</a></li>
    <li><a href=docs/Transfer_Learning.md>Transfer Learning</a></li>
    <li><a href=docs/Optical_Flow.md>Optical Flow</a></li>
    <li><a href=docs/Reinforcement_Learning.md>Reinforcement Learning</a></li>
    <li><a href=docs/Graph_Neural_Networks.md>Graph Neural Networks</a></li>
    <li><a href=docs/Latent_Space_LLM.md>Latent Space LLM</a></li>
  </ol>
