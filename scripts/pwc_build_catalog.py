"""CLI entry point for building the PapersWithCode Archive Catalog.

All logic lives in the ``scripts.catalog`` package; this file
only parses CLI arguments and delegates to :func:`build_catalog`.
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.catalog import build_catalog  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a markdown catalog from normalized PapersWithCode archive records.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/pwc_archive/normalized/papers"),
        help="Directory containing normalized paper JSON files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/pwc/index.md"),
        help="Markdown output path.",
    )
    args = parser.parse_args()

    records = build_catalog(args.input_dir, args.output)
    print(f"Wrote catalog page to {args.output} with {len(records)} records")


if __name__ == "__main__":
    main()
