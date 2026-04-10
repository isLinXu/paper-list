import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.pwc_seed_from_archive import build_seed_rows, cached_seed_path


class TestPwcSeedFromArchive(unittest.TestCase):
    @patch("scripts.pwc_seed_from_archive.fetch_archive_html")
    def test_build_seed_rows(self, mock_fetch):
        mock_fetch.return_value = (
            """
            <html><body>
              <a href="/paper/demo-paper">Paper</a>
              <a href="/task/demo-task">Task</a>
            </body></html>
            """,
            "https://web.archive.org/web/20250616051252/https://paperswithcode.com/",
        )
        with tempfile.TemporaryDirectory() as td:
            rows = build_seed_rows(
                ["https://web.archive.org/web/20250616051252/https://paperswithcode.com/"],
                Path(td),
                limit=10,
            )
        self.assertEqual(rows[0]["entity_type"], "paper")
        self.assertIn("/paper/demo-paper", rows[0]["archive_url"])

    @patch("scripts.pwc_seed_from_archive.fetch_archive_html")
    def test_build_seed_rows_uses_cache(self, mock_fetch):
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td)
            cache_path = cached_seed_path(output_dir, "https://web.archive.org/web/20250616051252/https://paperswithcode.com/")
            cache_path.write_text('<a href="/paper/cached-paper">cached</a>', encoding="utf-8")
            rows = build_seed_rows(
                ["https://web.archive.org/web/20250616051252/https://paperswithcode.com/"],
                output_dir,
                limit=10,
                use_cache=True,
            )
        mock_fetch.assert_not_called()
        self.assertIn("/paper/cached-paper", rows[0]["archive_url"])
