import unittest
from unittest.mock import Mock, patch

from scripts.pwc_fetch_archive import fetch_archive_html
from utils.pwc_archive import manifest_row_filename


class TestPwcFetchHelpers(unittest.TestCase):
    def test_manifest_row_filename(self):
        filename = manifest_row_filename({"entity_type": "paper", "id": "abc123"})
        self.assertEqual(filename, "paper--abc123.html")

    @patch("scripts.pwc_fetch_archive.requests.get")
    def test_fetch_archive_html(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.text = "<html>demo</html>"
        response.url = "https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo"
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        html, final_url = fetch_archive_html("https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo")
        self.assertIn("demo", html)
        self.assertIn("/paper/demo", final_url)

    @patch("scripts.pwc_fetch_archive.time.sleep")
    @patch("scripts.pwc_fetch_archive.requests.get")
    def test_fetch_archive_html_retries_429(self, mock_get, mock_sleep):
        rate_limited = Mock()
        rate_limited.status_code = 429
        rate_limited.url = "https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo"
        rate_limited.headers = {}
        success = Mock()
        success.status_code = 200
        success.text = "<html>ok</html>"
        success.url = rate_limited.url
        success.raise_for_status.return_value = None
        mock_get.side_effect = [rate_limited, success]
        html, _ = fetch_archive_html(rate_limited.url, max_retries=2)
        self.assertIn("ok", html)
        mock_sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
