import unittest

from utils.analytics.aggregate import (
    aggregate_code_coverage_daily,
    aggregate_daily_counts,
    aggregate_monthly_counts,
    aggregate_top_first_authors,
    parse_first_author,
)


class TestAnalyticsAggregate(unittest.TestCase):
    def setUp(self):
        # 极小样例：2 个 topic，跨 2 天，含/不含 code_url
        self.store = {
            "LLM": {
                "2401.00001": {
                    "date": "2026-03-01",
                    "title": "t1",
                    "authors": "Alice Zhang et.al.",
                    "arxiv_id": "2401.00001",
                    "pdf_url": "https://arxiv.org/abs/2401.00001",
                    "translate_url": "https://papers.cool/arxiv/2401.00001",
                    "read_url": "https://hjfy.top/arxiv/2401.00001",
                    "code_url": "https://github.com/a/b",
                },
                "2401.00002": {
                    "date": "2026-03-01",
                    "title": "t2",
                    "authors": "Bob Li et.al.",
                    "arxiv_id": "2401.00002",
                    "pdf_url": "https://arxiv.org/abs/2401.00002",
                    "translate_url": "https://papers.cool/arxiv/2401.00002",
                    "read_url": "https://hjfy.top/arxiv/2401.00002",
                    "code_url": None,
                },
            },
            "Multimodal": {
                "2401.00003": {
                    "date": "2026-03-02",
                    "title": "t3",
                    "authors": "Alice Zhang et.al.",
                    "arxiv_id": "2401.00003",
                    "pdf_url": "https://arxiv.org/abs/2401.00003",
                    "translate_url": "https://papers.cool/arxiv/2401.00003",
                    "read_url": "https://hjfy.top/arxiv/2401.00003",
                    "code_url": "https://github.com/c/d",
                }
            },
        }

    def test_parse_first_author(self):
        self.assertEqual(parse_first_author("Alice Zhang et.al."), "Alice Zhang")
        self.assertEqual(parse_first_author("Alice Zhang et al."), "Alice Zhang")
        self.assertEqual(parse_first_author("Alice Zhang"), "Alice Zhang")

    def test_daily_counts(self):
        rows = aggregate_daily_counts(self.store)
        # 2026-03-01 LLM count=2
        self.assertIn({"topic": "LLM", "date": "2026-03-01", "count": 2}, rows)

    def test_monthly_counts(self):
        rows = aggregate_monthly_counts(self.store)
        self.assertIn({"topic": "LLM", "date": "2026-03", "count": 2}, rows)
        self.assertIn({"topic": "Multimodal", "date": "2026-03", "count": 1}, rows)

    def test_code_coverage_daily(self):
        rows = aggregate_code_coverage_daily(self.store)
        self.assertIn(
            {
                "topic": "LLM",
                "date": "2026-03-01",
                "total": 2,
                "code_covered": 1,
                "code_coverage": 0.5,
            },
            rows,
        )

    def test_top_first_authors(self):
        top = aggregate_top_first_authors(
            self.store, start_date="2026-03-01", end_date="2026-03-02", top_n=3
        )
        # Alice: 2 papers
        self.assertEqual(top[0]["author"], "Alice Zhang")
        self.assertEqual(top[0]["count"], 2)


if __name__ == "__main__":
    unittest.main()

