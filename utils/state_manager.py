"""
SQLite state manager for paper-list pipeline.

Provides structured, persistent, and queryable state tracking replacing
the previous JSON-based state files (bulk_sync_state.json, fetch_state.json).

Schema
------
archive_fetch_log   — per-row Wayback fetch attempt log
openalex_cache      — OpenAlex API response cache with TTL
pipeline_checkpoint — incremental checkpoint per pipeline run
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_DB_PATH = Path(os.environ.get("PAPER_LIST_DB_PATH", "data/pwc_archive/staging/paper_list.db"))
_CON: sqlite3.Connection | None = None
_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    global _CON
    if _CON is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CON = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _CON.execute("PRAGMA journal_mode=WAL")
        _CON.execute("PRAGMA busy_timeout=5000")
        _CON.execute("PRAGMA foreign_keys=ON")
        _init_schema(_CON)
    return _CON


def _init_schema(con: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    con.executescript("""
    CREATE TABLE IF NOT EXISTS archive_fetch_log (
        id              TEXT PRIMARY KEY,
        archive_url     TEXT NOT NULL,
        entity_type     TEXT,
        fetch_status    TEXT NOT NULL DEFAULT 'pending',
        raw_html_path   TEXT,
        retry_count     INTEGER NOT NULL DEFAULT 0,
        last_error      TEXT,
        http_status     INTEGER,
        fetched_at      REAL,
        created_at      REAL NOT NULL DEFAULT (unixepoch()),
        updated_at      REAL NOT NULL DEFAULT (unixepoch())
    );

    CREATE TABLE IF NOT EXISTS openalex_cache (
        cache_key        TEXT PRIMARY KEY,
        response_json    TEXT NOT NULL,
        request_url      TEXT,
        created_at       REAL NOT NULL DEFAULT (unixepoch()),
        expires_at       REAL NOT NULL,
        hit_count        INTEGER NOT NULL DEFAULT 0,
        last_hit_at      REAL
    );

    CREATE TABLE IF NOT EXISTS pipeline_checkpoint (
        pipeline_name  TEXT PRIMARY KEY,
        run_id         TEXT NOT NULL,
        checkpoint_at  REAL NOT NULL DEFAULT (unixepoch()),
        total_rows     INTEGER,
        processed_rows INTEGER NOT NULL DEFAULT 0,
        failed_rows    INTEGER NOT NULL DEFAULT 0,
        metadata_json  TEXT
    );

    CREATE TABLE IF NOT EXISTS github_code_cache (
        arxiv_id    TEXT PRIMARY KEY,
        code_url    TEXT,
        fetched_at  REAL NOT NULL DEFAULT (unixepoch()),
        expires_at  REAL NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_fetch_status
        ON archive_fetch_log(fetch_status);
    CREATE INDEX IF NOT EXISTS idx_fetch_entity
        ON archive_fetch_log(entity_type);
    CREATE INDEX IF NOT EXISTS idx_cache_expires
        ON openalex_cache(expires_at);
    CREATE INDEX IF NOT EXISTS idx_ghcode_expires
        ON github_code_cache(expires_at);

    CREATE TABLE IF NOT EXISTS topic_fetch_log (
        topic           TEXT NOT NULL,
        bucket_index    INTEGER NOT NULL DEFAULT 0,
        query_hash      TEXT NOT NULL,
        fetch_status    TEXT NOT NULL DEFAULT 'success',
        papers_found    INTEGER NOT NULL DEFAULT 0,
        papers_new      INTEGER NOT NULL DEFAULT 0,
        started_at      REAL NOT NULL DEFAULT (unixepoch()),
        finished_at     REAL NOT NULL DEFAULT (unixepoch()),
        error_msg       TEXT,
        PRIMARY KEY (topic, bucket_index, query_hash)
    );

    CREATE INDEX IF NOT EXISTS idx_topic_fetch_time
        ON topic_fetch_log(topic, finished_at DESC);
    """)


def con() -> sqlite3.Connection:
    """Return the shared SQLite connection.

    All callers should use the _LOCK when performing write operations
    to ensure thread safety. Read operations are safe without the lock
    due to WAL journal mode.
    """
    with _LOCK:
        return _get_db()


def close() -> None:
    global _CON
    with _LOCK:
        if _CON is not None:
            _CON.close()
            _CON = None


# ---------------------------------------------------------------------------
# Archive fetch log
# ---------------------------------------------------------------------------

def upsert_fetch_row(
    archive_url: str,
    entity_type: str | None = None,
    fetch_status: str = "pending",
    raw_html_path: str | None = None,
    retry_count: int = 0,
    last_error: str | None = None,
    http_status: int | None = None,
) -> None:
    """Insert or update a fetch log row."""
    row_id = _stable_id(archive_url)
    now = time.time()
    with _LOCK:
        con().execute(
            """
            INSERT INTO archive_fetch_log
                (id, archive_url, entity_type, fetch_status, raw_html_path,
                 retry_count, last_error, http_status, fetched_at, updated_at)
            VALUES
                (:id, :url, :etype, :status, :path, :retry, :err, :http, :fetched, :now)
            ON CONFLICT(id) DO UPDATE SET
                fetch_status   = excluded.fetch_status,
                raw_html_path  = excluded.raw_html_path,
                retry_count    = excluded.retry_count,
                last_error     = excluded.last_error,
                http_status    = excluded.http_status,
                fetched_at     = excluded.fetched_at,
                updated_at     = excluded.updated_at,
                entity_type    = COALESCE(excluded.entity_type, entity_type)
            """,
            dict(
                id=str(row_id),
                url=archive_url,
                etype=entity_type,
                status=fetch_status,
                path=raw_html_path,
                retry=retry_count,
                err=last_error,
                http=http_status,
                fetched=now if fetch_status in ("fetched", "cached") else None,
                now=now,
            ),
        )


def update_fetch_status(
    archive_url: str,
    fetch_status: str,
    raw_html_path: str | None = None,
    last_error: str | None = None,
    http_status: int | None = None,
) -> None:
    """Update only the status fields of an existing row."""
    row_id = _stable_id(archive_url)
    now = time.time()
    with _LOCK:
        con().execute(
            """
            UPDATE archive_fetch_log
            SET fetch_status   = :status,
                raw_html_path  = COALESCE(:path, raw_html_path),
                last_error     = :err,
                http_status    = :http,
                fetched_at     = CASE WHEN :status IN ('fetched','cached')
                                      THEN :now ELSE fetched_at END,
                updated_at     = :now
            WHERE id = :id
            """,
            dict(
                id=str(row_id),
                status=fetch_status,
                path=raw_html_path,
                err=last_error,
                http=http_status,
                now=now,
            ),
        )


def increment_retry(archive_url: str) -> int:
    """Increment retry_count and return the new value. Returns -1 if row not found."""
    row_id = _stable_id(archive_url)
    with _LOCK:
        c = con()
        c.execute(
            "UPDATE archive_fetch_log SET retry_count = retry_count + 1 WHERE id = :id",
            dict(id=str(row_id)),
        )
        row = c.execute(
            "SELECT retry_count FROM archive_fetch_log WHERE id = :id", dict(id=str(row_id))
        ).fetchone()
        return row[0] if row else -1


def get_fetch_stats() -> dict[str, int]:
    """Return aggregate fetch statistics."""
    with con() as c:
        rows = c.execute(
            """
            SELECT fetch_status, COUNT(*) as cnt
            FROM archive_fetch_log
            GROUP BY fetch_status
            """
        ).fetchall()
    return dict(rows)


def get_blocked_rows(limit: int = 100) -> list[dict]:
    """Return rows that are rate-limited (status='rate_limited')."""
    with con() as c:
        rows = c.execute(
            """
            SELECT id, archive_url, entity_type, retry_count, last_error, fetched_at
            FROM archive_fetch_log
            WHERE fetch_status = 'rate_limited'
            ORDER BY fetched_at ASC
            LIMIT :limit
            """,
            dict(limit=limit),
        ).fetchall()
    cols = ["id", "archive_url", "entity_type", "retry_count", "last_error", "fetched_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_pending_rows(limit: int = 100) -> list[dict]:
    """Return rows that are still pending."""
    with con() as c:
        rows = c.execute(
            """
            SELECT id, archive_url, entity_type, retry_count
            FROM archive_fetch_log
            WHERE fetch_status IN ('pending', 'error')
            ORDER BY retry_count ASC, updated_at ASC
            LIMIT :limit
            """,
            dict(limit=limit),
        ).fetchall()
    cols = ["id", "archive_url", "entity_type", "retry_count"]
    return [dict(zip(cols, r)) for r in rows]


# ---------------------------------------------------------------------------
# OpenAlex cache
# ---------------------------------------------------------------------------

# Default TTL: 30 days
_DEFAULT_TTL_DAYS = 30


def cache_openalex(cache_key: str, response_json: str, request_url: str, ttl_days: int = _DEFAULT_TTL_DAYS) -> None:
    """Store an OpenAlex API response."""
    now = time.time()
    expires_at = now + ttl_days * 86400
    with _LOCK:
        con().execute(
            """
            INSERT INTO openalex_cache
                (cache_key, response_json, request_url, created_at, expires_at)
            VALUES (:key, :json, :url, :now, :exp)
            ON CONFLICT(cache_key) DO UPDATE SET
                response_json = excluded.response_json,
                request_url   = excluded.request_url,
                created_at    = excluded.created_at,
                expires_at    = excluded.expires_at
            """,
            dict(key=cache_key, json=response_json, url=request_url, now=now, exp=expires_at),
        )


def get_cached_openalex(cache_key: str) -> dict | None:
    """Retrieve a cached OpenAlex response, or None if expired/missing."""
    now = time.time()
    with _LOCK:
        row = con().execute(
            """
            SELECT response_json, expires_at FROM openalex_cache
            WHERE cache_key = :key AND expires_at > :now
            """,
            dict(key=cache_key, now=now),
        ).fetchone()
    if row:
        # Increment hit count (best-effort, non-blocking)
        try:
            with _LOCK:
                con().execute(
                    "UPDATE openalex_cache SET hit_count = hit_count + 1, last_hit_at = :now WHERE cache_key = :key",
                    dict(key=cache_key, now=time.time()),
                )
        except Exception:
            pass
        return json.loads(row[0])
    return None


def cache_openalex_by_doi(doi: str, response_json: str, request_url: str, ttl_days: int = _DEFAULT_TTL_DAYS) -> None:
    cache_openalex(f"doi:{doi}", response_json, request_url, ttl_days)


def get_cached_openalex_by_doi(doi: str) -> dict | None:
    return get_cached_openalex(f"doi:{doi}")


def cache_openalex_by_arxiv(arxiv_id: str, response_json: str, request_url: str, ttl_days: int = _DEFAULT_TTL_DAYS) -> None:
    cache_openalex(f"arxiv:{arxiv_id}", response_json, request_url, ttl_days)


def get_cached_openalex_by_arxiv(arxiv_id: str) -> dict | None:
    return get_cached_openalex(f"arxiv:{arxiv_id}")


def cache_openalex_by_title(title: str, response_json: str, request_url: str, ttl_days: int = _DEFAULT_TTL_DAYS) -> None:
    cache_openalex(f"title:{title}", response_json, request_url, ttl_days)


def get_cached_openalex_by_title(title: str) -> dict | None:
    return get_cached_openalex(f"title:{title}")


def get_cache_stats() -> dict[str, Any]:
    """Return cache statistics."""
    with con() as c:
        total = c.execute("SELECT COUNT(*) FROM openalex_cache").fetchone()[0]
        expired = c.execute(
            "SELECT COUNT(*) FROM openalex_cache WHERE expires_at < :now",
            dict(now=time.time()),
        ).fetchone()[0]
        total_hits = c.execute("SELECT SUM(hit_count) FROM openalex_cache").fetchone()[0] or 0
    return dict(total=total, expired=expired, total_hits=total_hits)


def cleanup_expired_cache() -> int:
    """Delete expired cache entries. Returns count of deleted rows."""
    now = time.time()
    with _LOCK:
        cur = con().execute(
            "DELETE FROM openalex_cache WHERE expires_at < :now",
            dict(now=now),
        )
    return cur.rowcount


# ---------------------------------------------------------------------------
# Pipeline checkpoint
# ---------------------------------------------------------------------------

def upsert_checkpoint(
    pipeline_name: str,
    run_id: str,
    total_rows: int | None = None,
    processed_rows: int | None = None,
    failed_rows: int | None = None,
    metadata: dict | None = None,
) -> None:
    """Create or update a pipeline checkpoint."""
    with _LOCK:
        con().execute(
            """
            INSERT INTO pipeline_checkpoint
                (pipeline_name, run_id, checkpoint_at, total_rows, processed_rows, failed_rows, metadata_json)
            VALUES (:name, :run, :now, :total, :processed,
                    COALESCE(:failed, 0), :meta)
            ON CONFLICT(pipeline_name) DO UPDATE SET
                run_id          = excluded.run_id,
                checkpoint_at   = excluded.checkpoint_at,
                total_rows      = COALESCE(excluded.total_rows, total_rows),
                processed_rows  = excluded.processed_rows,
                failed_rows     = COALESCE(excluded.failed_rows, failed_rows),
                metadata_json   = excluded.metadata_json
            """,
            dict(
                name=pipeline_name,
                run=run_id,
                now=time.time(),
                total=total_rows,
                processed=processed_rows,
                failed=failed_rows,
                meta=json.dumps(metadata) if metadata else None,
            ),
        )


def get_checkpoint(pipeline_name: str) -> dict | None:
    """Return checkpoint for a pipeline, or None."""
    with con() as c:
        row = c.execute(
            "SELECT * FROM pipeline_checkpoint WHERE pipeline_name = :name",
            dict(name=pipeline_name),
        ).fetchone()
    if row is None:
        return None
    cols = ["pipeline_name", "run_id", "checkpoint_at", "total_rows",
            "processed_rows", "failed_rows", "metadata_json"]
    result = dict(zip(cols, row))
    if result["metadata_json"]:
        result["metadata"] = json.loads(result["metadata_json"])
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stable_id(archive_url: str) -> str:
    """Deterministic ID for an archive URL (matches utils.pwc_archive.stable_id)."""
    import hashlib
    return hashlib.md5(archive_url.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Import compatibility shim
# ---------------------------------------------------------------------------

def manifest_row_filename(row: dict) -> str:
    """Alias for backward compatibility with scripts/pwc_fetch_archive.py."""
    from utils.pwc_archive import manifest_row_filename as _orig
    return _orig(row)


def load_json(file_path: Path | str, default: Any = None) -> Any:
    """Alias for backward compatibility."""
    from utils.pwc_archive import load_json as _orig
    return _orig(file_path, default)


def dump_json(file_path: Path | str, data: Any) -> None:
    """Alias for backward compatibility."""
    from utils.pwc_archive import dump_json as _orig
    return _orig(file_path, data)


# ---------------------------------------------------------------------------
# GitHub code cache
# ---------------------------------------------------------------------------

_DEFAULT_GHCODE_TTL_DAYS = 7


def cache_github_code(arxiv_id: str, code_url: str | None,
                      ttl_days: int = _DEFAULT_GHCODE_TTL_DAYS) -> None:
    """Store a GitHub code URL (or None = not found) for an arXiv paper."""
    now = time.time()
    expires_at = now + ttl_days * 86400
    with _LOCK:
        con().execute(
            """
            INSERT INTO github_code_cache (arxiv_id, code_url, fetched_at, expires_at)
            VALUES (:id, :url, :now, :exp)
            ON CONFLICT(arxiv_id) DO UPDATE SET
                code_url   = excluded.code_url,
                fetched_at = excluded.fetched_at,
                expires_at = excluded.expires_at
            """,
            dict(id=arxiv_id, url=code_url, now=now, exp=expires_at),
        )


def get_cached_github_code(arxiv_id: str) -> tuple[bool, str | None]:
    """Return (found_in_cache, code_url).

    found_in_cache=True means we have a valid (non-expired) cache entry.
    code_url may be None meaning the paper has no public code repo.
    """
    now = time.time()
    with _LOCK:
        row = con().execute(
            "SELECT code_url FROM github_code_cache WHERE arxiv_id = :id AND expires_at > :now",
            dict(id=arxiv_id, now=now),
        ).fetchone()
    if row is None:
        return False, None
    return True, row[0]


def cleanup_expired_github_cache() -> int:
    """Delete expired GitHub code cache entries. Returns count of deleted rows."""
    now = time.time()
    with _LOCK:
        cur = con().execute(
            "DELETE FROM github_code_cache WHERE expires_at < :now",
            dict(now=now),
        )
    return cur.rowcount


# ---------------------------------------------------------------------------
# Topic fetch log (incremental fetch support)
# ---------------------------------------------------------------------------

def log_topic_fetch(
    topic: str,
    bucket_index: int = 0,
    query_hash: str = "",
    fetch_status: str = "success",
    papers_found: int = 0,
    papers_new: int = 0,
    error_msg: str | None = None,
) -> None:
    """Record a topic fetch attempt in the database."""
    now = time.time()
    with _LOCK:
        con().execute(
            """
            INSERT INTO topic_fetch_log
                (topic, bucket_index, query_hash, fetch_status,
                 papers_found, papers_new, started_at, finished_at, error_msg)
            VALUES
                (:topic, :bucket, :qhash, :status,
                 :found, :new, :started, :finished, :err)
            ON CONFLICT(topic, bucket_index, query_hash) DO UPDATE SET
                fetch_status   = excluded.fetch_status,
                papers_found   = excluded.papers_found,
                papers_new     = excluded.papers_new,
                finished_at    = excluded.finished_at,
                error_msg      = excluded.error_msg
            """,
            dict(
                topic=topic, bucket=bucket_index, qhash=query_hash,
                status=fetch_status, found=papers_found, new=papers_new,
                started=now, finished=now, err=error_msg,
            ),
        )


def get_topic_last_fetch(topic: str) -> dict | None:
    """Return the most recent successful fetch for a topic, or None."""
    with con() as c:
        row = c.execute(
            """
            SELECT topic, bucket_index, fetch_status, papers_found, papers_new,
                   started_at, finished_at
            FROM topic_fetch_log
            WHERE topic = :topic AND fetch_status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1
            """,
            dict(topic=topic),
        ).fetchone()
    if row is None:
        return None
    cols = ["topic", "bucket_index", "fetch_status", "papers_found",
            "papers_new", "started_at", "finished_at"]
    return dict(zip(cols, row))


def get_all_topic_last_fetches() -> dict[str, dict]:
    """Return {topic: last_fetch_info} for all topics with successful fetches."""
    with con() as c:
        rows = c.execute(
            """
            SELECT topic, MAX(finished_at) as last_fetch,
                   SUM(papers_found) as total_found,
                   SUM(papers_new) as total_new
            FROM topic_fetch_log
            WHERE fetch_status = 'success'
            GROUP BY topic
            """
        ).fetchall()
    result = {}
    for row in rows:
        result[row[0]] = {
            "last_fetch": row[1],
            "total_found": row[2],
            "total_new": row[3],
        }
    return result
