import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_step(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small-batch PapersWithCode archive pipeline.")
    parser.add_argument("--from-timestamp", default=None)
    parser.add_argument("--to-timestamp", default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--mailto", default=None)
    parser.add_argument("--seed-archive-url", action="append", dest="seed_archive_urls", default=[])
    parser.add_argument("--use-local-seeds", action="store_true")
    parser.add_argument("--reuse-existing-manifest", action="store_true")
    parser.add_argument("--reuse-existing-fetch-state", action="store_true")
    parser.add_argument("--skip-cdx", action="store_true")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-parse", action="store_true")
    parser.add_argument("--skip-openalex", action="store_true")
    parser.add_argument("--skip-github", action="store_true")
    args = parser.parse_args()

    rows = []
    manifest_path = PROJECT_ROOT / "data/pwc_archive/staging/cdx_manifest.json"
    fetch_state = PROJECT_ROOT / "data/pwc_archive/staging/fetch_state.json"

    if args.reuse_existing_manifest and manifest_path.exists():
        pass
    elif args.use_local_seeds:
        merge_cmd = [
            sys.executable,
            "scripts/pwc_merge_seed_sources.py",
            "--limit",
            str(args.limit * 4),
            "--manifest",
            "data/pwc_archive/staging/seed_manifest.json",
            "--manifest",
            "data/pwc_archive/staging/discovery_manifest.json",
        ]
        run_step(merge_cmd)
        local_manifest = PROJECT_ROOT / "data/pwc_archive/staging/local_seed_manifest.json"
        if local_manifest.exists():
            manifest_path.write_text(local_manifest.read_text(encoding="utf-8"), encoding="utf-8")
    elif args.seed_archive_urls:
        seed_cmd = [
            sys.executable,
            "scripts/pwc_seed_from_archive.py",
            "--limit",
            str(args.limit * 4),
            "--continue-on-error",
        ]
        for archive_url in args.seed_archive_urls:
            seed_cmd.extend(["--archive-url", archive_url])
        run_step(seed_cmd)
        seed_manifest = PROJECT_ROOT / "data/pwc_archive/staging/seed_manifest.json"
        if seed_manifest.exists():
            manifest_path.write_text(seed_manifest.read_text(encoding="utf-8"), encoding="utf-8")
    elif not args.skip_cdx:
        cdx_cmd = [sys.executable, "scripts/pwc_cdx_discover.py", "--limit", str(args.limit * 4)]
        if args.from_timestamp:
            cdx_cmd.extend(["--from-timestamp", args.from_timestamp])
        if args.to_timestamp:
            cdx_cmd.extend(["--to-timestamp", args.to_timestamp])
        cdx_cmd.append("--continue-on-error")
        run_step(cdx_cmd)

    if not args.skip_fetch and not (args.reuse_existing_fetch_state and fetch_state.exists()):
        run_step(
            [
                sys.executable,
                "scripts/pwc_fetch_archive.py",
                "--entity-type",
                "paper",
                "--limit",
                str(args.limit),
                "--continue-on-error",
            ]
        )

    if fetch_state.exists():
        rows = json.loads(fetch_state.read_text(encoding="utf-8"))

    parsed_outputs: list[str] = []
    if not args.skip_parse:
        for row in rows:
            if not row.get("raw_html_path"):
                continue
            output = PROJECT_ROOT / "data/pwc_archive/normalized/papers" / (Path(row["raw_html_path"]).stem + ".json")
            parsed_outputs.append(str(output))
            run_step(
                [
                    sys.executable,
                    "scripts/pwc_parse_pages.py",
                    "--input-html",
                    row["raw_html_path"],
                    "--archive-url",
                    row["archive_url"],
                    "--output",
                    str(output),
                ]
            )

    if not args.skip_openalex and parsed_outputs:
        openalex_cmd = [sys.executable, "scripts/pwc_enrich_openalex.py"]
        if args.mailto:
            openalex_cmd.extend(["--mailto", args.mailto])
        for parsed_output in parsed_outputs:
            openalex_cmd.extend(["--input", parsed_output])
        run_step(openalex_cmd)

    if not args.skip_github and parsed_outputs:
        for parsed_output in parsed_outputs:
            run_step([sys.executable, "scripts/pwc_enrich_github.py", "--input", parsed_output])

    run_step([sys.executable, "scripts/pwc_build_catalog.py"])


if __name__ == "__main__":
    main()
