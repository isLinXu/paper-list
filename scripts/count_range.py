import json
import sys
import re
import datetime
from collections import OrderedDict
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/count_range.py <start_date> <end_date> [json_path]")
        sys.exit(1)

    start_date = datetime.date.fromisoformat(sys.argv[1])
    end_date = datetime.date.fromisoformat(sys.argv[2])
    json_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('docs/paper_list.json')

    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(2)

    with open(json_path, 'r') as f:
        data = json.load(f)

    rx = re.compile(r"\|\*\*(\d{4}-\d{2}-\d{2})\*\*\|")

    counts = OrderedDict()
    total = 0
    min_d = None
    max_d = None

    for cat, items in data.items():
        c = 0
        for k, v in items.items():
            m = rx.search(v)
            if not m:
                continue
            d = datetime.date.fromisoformat(m.group(1))
            if start_date <= d <= end_date:
                c += 1
                total += 1
                min_d = d if (min_d is None or d < min_d) else min_d
                max_d = d if (max_d is None or d > max_d) else max_d
        counts[cat] = c

    print(f"Date range: {start_date} to {end_date}")
    print(f"Items in range: {total}")
    print(f"Earliest date found: {min_d}")
    print(f"Latest date found: {max_d}")
    print("")
    for cat, c in counts.items():
        print(f"{cat}: {c}")


if __name__ == "__main__":
    main()