import tempfile
import unittest
from pathlib import Path

from scripts.pwc_build_catalog import build_catalog
from utils.pwc_archive import dump_json


class TestPwcBuildCatalog(unittest.TestCase):
    def test_build_catalog_generates_facet_pages(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_dir = root / "data"
            output = root / "docs/pwc/index.md"
            input_dir.mkdir(parents=True)

            dump_json(
                input_dir / "record.json",
                {
                    "title": "Demo Vision Transformer for Segmentation",
                    "publication_year": 2025,
                    "paper_url": "https://arxiv.org/abs/2505.00001",
                    "repo_url": "https://github.com/example/demo-seg",
                    "tasks": ["Semantic Segmentation"],
                    "methods": ["Vision Transformer"],
                    "architecture": ["Vision Transformer"],
                    "frameworks": ["PyTorch"],
                    "datasets": ["ADE20K"],
                    "benchmarks": ["ADE20K validation"],
                    "repo_topics": ["semantic-segmentation", "vision-transformer"],
                    "archive_page_url": "https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo-seg",
                },
            )

            records = build_catalog(input_dir, output)

            self.assertEqual(len(records), 1)
            self.assertTrue(output.exists())
            self.assertTrue((root / "docs/pwc/tasks/index.md").exists())
            self.assertTrue((root / "docs/pwc/tasks/semantic-segmentation.md").exists())
            self.assertTrue((root / "docs/pwc/methods/vision-transformer.md").exists())
            self.assertTrue((root / "docs/pwc/frameworks/pytorch.md").exists())
            self.assertTrue((root / "docs/pwc/datasets/ade20k.md").exists())
            self.assertTrue((root / "docs/pwc/benchmarks/ade20k-validation.md").exists())
            self.assertTrue((root / "docs/pwc/analytics/index.md").exists())
            self.assertTrue((root / "docs/pwc/review/index.md").exists())

            index_text = output.read_text(encoding="utf-8")
            self.assertIn("tasks/", index_text)
            self.assertIn("architectures/", index_text)
            self.assertIn("datasets/", index_text)
            self.assertIn("analytics/", index_text)
            self.assertIn("review/", index_text)
            self.assertIn("Repository topics", (root / "docs/pwc/tasks/semantic-segmentation.md").read_text(encoding="utf-8"))
            self.assertIn("Top tasks", (root / "docs/pwc/analytics/index.md").read_text(encoding="utf-8"))
            review_text = (root / "docs/pwc/review/index.md").read_text(encoding="utf-8")
            self.assertIn("Flagged records", review_text)
            self.assertIn("Suggested next steps", review_text)
            self.assertIn("Suggested commands", review_text)
            self.assertIn("python scripts/pwc_build_catalog.py", review_text)
            self.assertIn("priority", review_text)
            self.assertIn("Sparse provenance", review_text)


if __name__ == "__main__":
    unittest.main()
