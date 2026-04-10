import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.pwc_cdx_discover import build_manifest, fetch_cdx_rows
from utils.pwc_archive import decode_github_readme, enrich_with_github, enrich_with_openalex, load_json


class TestPwcCdxDiscover(unittest.TestCase):
    def test_build_manifest(self):
        manifest = build_manifest(
            [
                {
                    "timestamp": "20250616051252",
                    "original": "https://paperswithcode.com/paper/demo",
                    "statuscode": "200",
                    "mimetype": "text/html",
                }
            ]
        )
        self.assertEqual(manifest[0]["entity_type"], "paper")
        self.assertIn("/web/20250616051252/", manifest[0]["archive_url"])

    @patch("scripts.pwc_cdx_discover.requests.get")
    def test_fetch_cdx_rows(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype"],
            ["20250616051252", "https://paperswithcode.com/paper/demo", "200", "text/html"],
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        rows = fetch_cdx_rows("https://web.archive.org/cdx/search/cdx", "/paper/*")
        self.assertEqual(rows[0]["original"], "https://paperswithcode.com/paper/demo")


class TestPwcEnrichment(unittest.TestCase):
    def test_enrich_with_openalex(self):
        record = {
            "paper_id": "demo",
            "title": "Demo Title",
            "authors": [],
            "paper_url": "https://arxiv.org/abs/2505.00001",
            "repo_url": "https://github.com/example/demo",
            "source_provenance": [{"source": "paperswithcode-archive", "url": "https://web.archive.org/..."}],
            "confidence": {"paper_match": 0.6},
        }
        work = {
            "display_name": "Demo Title",
            "publication_year": 2025,
            "doi": "https://doi.org/10.1234/demo",
            "authorships": [{"author": {"display_name": "Jane Doe"}}],
            "primary_location": {"source": {"display_name": "CVPR"}},
            "concepts": [
                {"display_name": "Semantic Segmentation"},
                {"display_name": "Computer science"},
            ],
            "abstract_inverted_index": {"Demo": [0], "abstract": [1]},
        }
        enriched = enrich_with_openalex(record, work, "https://api.openalex.org/works?search=demo")
        self.assertEqual(enriched["publication_year"], 2025)
        self.assertEqual(enriched["venue"], "CVPR")
        self.assertEqual(enriched["doi"], "10.1234/demo")
        self.assertIn("Jane Doe", enriched["authors"])
        self.assertIn("Semantic Segmentation", enriched["methods"])
        self.assertNotIn("Computer science", enriched["methods"])

    def test_enrich_with_github(self):
        record = {
            "paper_id": "demo",
            "title": "Vision Transformer Demo",
            "authors": [],
            "repo_url": "https://github.com/example/demo",
            "repo_owner": "example",
            "repo_name": "demo",
            "frameworks": [],
            "architecture": [],
            "source_provenance": [],
            "confidence": {"repo_match": 0.5},
        }
        repo_payload = {
            "name": "demo",
            "description": "PyTorch vision transformer implementation for ADE20K val and ImageNet-1K",
            "homepage": "https://example.com/imagenet-1k-demo",
            "stargazers_count": 123,
            "license": {"spdx_id": "MIT"},
            "topics": ["semantic-segmentation", "vision-transformer", "imagenet-1k"],
        }
        languages_payload = {"Python": 90, "CUDA": 10}
        readme_text = """
        # Demo
        Built with PyTorch and CUDA.
        Evaluated on ADE20K val and ImageNet-1K.
        """
        enriched = enrich_with_github(
            record,
            repo_payload,
            languages_payload,
            "https://api.github.com/repos/example/demo",
            readme_text=readme_text,
        )
        self.assertEqual(enriched["license"], "MIT")
        self.assertEqual(enriched["stars_at_capture"], 123)
        self.assertIn("imagenet-1k-demo", enriched["repo_homepage"])
        self.assertIn("semantic-segmentation", enriched["repo_topics"])
        self.assertIn("Semantic Segmentation", enriched["tasks"])
        self.assertIn("PyTorch", enriched["frameworks"])
        self.assertIn("Vision Transformer", enriched["architecture"])
        self.assertIn("ADE20K", enriched["datasets"])
        self.assertIn("ImageNet-1K", enriched["benchmarks"])

    def test_decode_github_readme(self):
        payload = {
            "encoding": "base64",
            "content": "IyBUZXN0CkltYWdlTmV0LTFLIGFuZCBQeVRvcmNo",
        }
        decoded = decode_github_readme(payload)
        self.assertIn("PyTorch", decoded)
        self.assertIn("ImageNet-1K", decoded)


if __name__ == "__main__":
    unittest.main()
