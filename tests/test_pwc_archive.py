import tempfile
import unittest
from pathlib import Path

from utils.pwc_archive import extract_capture_timestamp, normalize_paper_record, parse_paper_page, resolve_archive_link


class TestPwcArchive(unittest.TestCase):
    def test_extract_capture_timestamp(self):
        stamp = extract_capture_timestamp(
            "https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo"
        )
        self.assertEqual(stamp, "2025-06-16T05:12:52Z")

    def test_normalize_paper_record_infers_labels(self):
        record = normalize_paper_record(
            {
                "title": "Mamba Diffusion Transformer",
                "abstract": "A PyTorch implementation with CUDA kernels.",
                "repo_url": "https://github.com/acme/demo",
            }
        )
        self.assertIn("Mamba", record["architecture"])
        self.assertIn("Diffusion", record["architecture"])
        self.assertIn("Transformer", record["architecture"])
        self.assertIn("PyTorch", record["frameworks"])
        self.assertIn("CUDA", record["frameworks"])

    def test_normalize_paper_record_infers_3d_tasks(self):
        record = normalize_paper_record(
            {
                "title": "MUSt3R: Multi-view Network for Stereo 3D Reconstruction",
                "abstract": "Designed for SfM and visual SLAM scenarios, with visual odometry, camera pose and multi-view depth estimation.",
                "repo_url": "https://github.com/naver/must3r",
            }
        )
        self.assertIn("3D Reconstruction", record["tasks"])
        self.assertIn("Depth Estimation", record["tasks"])
        self.assertIn("Visual Odometry", record["tasks"])
        self.assertIn("Visual SLAM", record["tasks"])
        self.assertIn("Structure from Motion", record["tasks"])
        self.assertIn("Multi-view Network", record["architecture"])

    def test_normalize_paper_record_infers_topics_from_repo_topics(self):
        record = normalize_paper_record(
            {
                "title": "Vision-language model demo",
                "abstract": "A compact project page.",
                "repo_url": "https://github.com/acme/demo",
                "repo_topics": ["object-detection", "multimodal", "imagenet-1k", "instance-segmentation"],
            }
        )
        self.assertIn("Object Detection", record["tasks"])
        self.assertIn("Multimodal Learning", record["tasks"])
        self.assertIn("Instance Segmentation", record["tasks"])
        self.assertIn("ImageNet-1K", record["benchmarks"])

    def test_parse_paper_page_smoke(self):
        html = """
        <html>
          <body>
            <h1>Demo Vision Transformer for Segmentation</h1>
            <p>2025</p>
            <p>This paper introduces a diffusion based model for semantic segmentation.</p>
            <a href="https://arxiv.org/abs/2505.00001">Paper</a>
            <a href="https://github.com/example/demo-seg">Code</a>
            <a href="/task/semantic-segmentation">Task</a>
            <a href="/method/vision-transformer">Method</a>
            <a href="/dataset/ade20k">Dataset</a>
            <a href="/benchmark/ade20k-val">Benchmark</a>
          </body>
        </html>
        """
        record = parse_paper_page(
            html,
            "https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo-seg",
        )
        self.assertEqual(record["title"], "Demo Vision Transformer for Segmentation")
        self.assertEqual(record["publication_year"], 2025)
        self.assertEqual(record["repo_url"], "https://github.com/example/demo-seg")
        self.assertIn("Vision Transformer", record["architecture"])
        self.assertIn("Semantic Segmentation", record["tasks"])
        self.assertIn("Vision Transformer", record["methods"])
        self.assertIn("Ade20k", record["datasets"])
        self.assertIn("Ade20k Val", record["benchmarks"])

    def test_resolve_archive_link(self):
        link = resolve_archive_link(
            "https://web.archive.org/web/20250616051252/https://paperswithcode.com/",
            "/paper/demo-seg",
        )
        self.assertEqual(
            link,
            "https://web.archive.org/web/20250616051252/https://paperswithcode.com/paper/demo-seg",
        )


if __name__ == "__main__":
    unittest.main()
