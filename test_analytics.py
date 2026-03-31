"""
Test entrypoint for `python -m unittest -v`.

This file intentionally re-exports tests from `tests/` so that the default
unittest discovery (current directory) can pick them up.
"""

from tests.test_analytics import *  # noqa: F401,F403

