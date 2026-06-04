"""
Utility functions for PapersWithCode (PWC) archive operations.

This module extracts the PWC-specific logic from pwc_archive.py,
providing a cleaner separation of concerns:
- pwc_archive.py: handles raw HTTP fetching and Wayback archiving
- pwc_utils.py: provides helper functions for data processing,
  enrichment, and GitHub fallback
"""

import re
from typing import Any

# Re-export stable_id for convenience
from .state_manager import stable_id


def extract_paper_links(html: str, base_url: str) -> list[str]:
    """Extract paper links from PWC HTML page."""
    links = re.findall(r'href="([^"]*)"', html)
    return [link for link in links if "/papers/" in link]


def extract_repo_url(html: str, base_url: str) -> str | None:
    """Try to extract the first GitHub repo URL from HTML."""
    match = re.search(r'https://github\.com/[^/]+/[^/]+', html)
    return match.group(0) if match else None


def try_hf_repo(arxiv_id: str) -> str | None:
    """Try to find a GitHub repo for the given arXiv ID.

    NOTE: HuggingFace connection is unstable and causes timeouts in
    GitHub Actions. Disabling it to ensure daily updates succeed.
    """
    return None


def extract_paper_id(html: str) -> str | None:
    """Extract the paper ID (e.g., 2108.09112v1 -> 2108.09112)."""
    match = re.search(r"\d{4}\.\d{4,5}(?:v\d+)?", html)
    return match.group(0) if match else None


def normalize_paper_id(raw_id: str) -> str:
    """Normalize a paper ID by removing version suffix."""
    match = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", raw_id)
    if match:
        return match.group(1)
    return raw_id.strip()


def build_paper_url(arxiv_id: str) -> str:
    """Build the full arXiv URL for a paper."""
    return f"https://arxiv.org/abs/{normalize_paper_id(arxiv_id)}"


def build_paperswithcode_url(arxiv_id: str) -> str:
    """Build the PapersWithCode URL for a paper."""
    return f"https://paperswithcode.com/paper/{normalize_paper_id(arxiv_id)}"


def build_hf_url(arxiv_id: str) -> str:
    """Build the HuggingFace URL for a paper."""
    return f"https://huggingface.co/papers/{normalize_paper_id(arxiv_id)}"


def build_github_search_url(arxiv_id: str) -> str:
    """Build a GitHub search URL for a paper's repository."""
    normalized = normalize_paper_id(arxiv_id)
    query = f"arxiv:{normalized}"
    return f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc"


def build_read_url(arxiv_id: str) -> str:
    """Build a reading URL for a paper."""
    normalized = normalize_paper_id(arxiv_id)
    return f"https://papers.cool/arxiv/{normalized}"


def build_translate_url(arxiv_id: str) -> str:
    """Build a translation URL for a paper."""
    normalized = normalize_paper_id(arxiv_id)
    return f"https://hjfy.top/arxiv/{normalized}"


def build_code_url(arxiv_id: str) -> str | None:
    """Build the code URL for a paper, if available."""
    # This function would contain the logic to find the code repository
    # for a given arXiv paper, potentially using GitHub search.
    return None
