import tempfile
import unittest
from pathlib import Path

from scripts.pwc_merge_seed_sources import merge_rows, rows_from_manual_urls


class TestPwcMergeSeedSources(unittest.TestCase):
    def test_rows_from_manual_urls(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manual_urls.txt"
            path.write_text(
                "# comment\nhttps://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo\n",
                encoding="utf-8",
            )
            rows = rows_from_manual_urls(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["entity_type"], "paper")

    def test_merge_rows_deduplicates(self):
        rows = merge_rows(
            [{"archive_url": "https://x/paper/a", "entity_type": "paper", "id": "1", "source": "a", "status": "pending"}],
            [{"archive_url": "https://x/paper/a", "entity_type": "paper", "id": "2", "source": "b", "status": "pending"}],
        )
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
