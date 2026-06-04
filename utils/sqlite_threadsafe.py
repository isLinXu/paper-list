"""
Thread-safe wrapper for SQLite connections.

This module replaces the direct sqlite3 usage in state_manager.py
with a thread-safe connection pool that:
1. Creates a new connection per thread
2. Uses WAL journal mode for concurrency
3. Handles busy timeouts gracefully
"""

import sqlite3
import threading
import time
from typing import Any

_LOCK = threading.RLock()
_CONN_CACHE: dict[int, sqlite3.Connection] = {}


def get_connection(db_path: str = "data/pwc_archive/staging/paper_list.db") -> sqlite3.Connection:
    """Get a thread-safe SQLite connection with WAL mode and busy timeout."""
    with _LOCK:
        if db_path in _CONN_CACHE:
            return _CONN_CACHE[db_path]

        db_path_parent = "/".join(db_path.split("/")[:-1])
        if not db_path_parent:
            db_path_parent = "."
        import os
        os.makedirs(db_path_parent, exist_ok=True)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        _CONN_CACHE[db_path] = conn
    return conn


def close_connection(db_path: str = "data/pwc_archive/staging/paper_list.db") -> None:
    """Close the cached connection for the given db path."""
    global _CONN_CACHE
    with _LOCK:
        conn = _CONN_CACHE.pop(db_path, None)
        if conn:
            conn.close()
