import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.pwc_archive import dump_json, parse_paper_page


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse archived PapersWithCode HTML pages into normalized paper records.")
    parser.add_argument("--input-html", type=Path, required=True, help="Local archived paper HTML file.")
    parser.add_argument("--archive-url", required=True, help="Wayback archive URL for provenance.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/pwc_archive/normalized/papers/sample.json"),
        help="Normalized JSON output path.",
    )
    args = parser.parse_args()

    html = args.input_html.read_text(encoding="utf-8")
    record = parse_paper_page(html, args.archive_url)
    dump_json(args.output, record)
    print(f"Wrote normalized paper record to {args.output}")


if __name__ == "__main__":
    main()
