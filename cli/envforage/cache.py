"""
Local SQLite caching for EnvForage CLI.

Stores diagnostic report snapshots and verification results in a lightweight
SQLite database at ~/.envforage/cache.db so repeated `diagnose` calls can
skip expensive I/O and provide instant offline output.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


_DEFAULT_DB_PATH = Path.home() / ".envforage" / "cache.db"

# Default TTL of 1 hour (3600 seconds). Entries older than this are stale.
_DEFAULT_TTL_SECONDS = 3600


class SQLiteCache:
    """
    A simple key-value cache backed by a local SQLite database.

    Each entry has:
      - key   : str  – unique cache key (e.g. "diagnose:hash:<sha256>")
      - value : str  – JSON-serialised payload
      - ttl   : int  – time-to-live in seconds (0 = never expire)
      - ts    : int  – Unix timestamp of insertion (seconds)

    Usage::

        cache = SQLiteCache()
        cache.set("my-key", {"result": 42}, ttl=600)
        data = cache.get("my-key")   # returns dict or None if missing/expired
        cache.delete("my-key")
        cache.clear()
    """

    def __init__(
        self,
        db_path: Path | str = _DEFAULT_DB_PATH,
        default_ttl: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self.db_path = Path(db_path)
        self.default_ttl = default_ttl
        self._init_db()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Return a new SQLite connection (thread-local, WAL mode)."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create the cache table if it does not already exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    ttl   INTEGER NOT NULL DEFAULT 0,
                    ts    INTEGER NOT NULL
                )
                """
            )

    def _is_expired(self, ttl: int, ts: int) -> bool:
        """Return True if the entry has reached or exceeded its TTL."""
        if ttl == 0:
            return False  # never expires
        return (time.time() - ts) >= ttl

    # ── Public API ──────────────────────────────────────────────────────────

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Insert or update a cache entry.

        Args:
            key:   Unique cache key string.
            value: Any JSON-serialisable Python object.
            ttl:   Time-to-live in seconds.  0 = immortal.
                   Defaults to ``self.default_ttl``.
        """
        effective_ttl = self.default_ttl if ttl is None else ttl
        serialised = json.dumps(value)
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cache (key, value, ttl, ts)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    ttl   = excluded.ttl,
                    ts    = excluded.ts
                """,
                (key, serialised, effective_ttl, now),
            )

    def get(self, key: str) -> Any | None:
        """
        Retrieve a cached value by key.

        Returns:
            The deserialised Python object, or ``None`` if the key does not
            exist or the entry has expired.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, ttl, ts FROM cache WHERE key = ?", (key,)
            ).fetchone()

        if row is None:
            return None

        if self._is_expired(row["ttl"], row["ts"]):
            # Lazily evict stale entry
            self.delete(key)
            return None

        return json.loads(row["value"])

    def delete(self, key: str) -> None:
        """Remove a single entry from the cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))

    def clear(self) -> None:
        """Remove **all** entries from the cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache")

    def purge_expired(self) -> int:
        """
        Delete all expired entries proactively.

        Returns:
            The number of rows deleted.
        """
        now = int(time.time())
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM cache WHERE ttl > 0 AND (? - ts) >= ttl", (now,)
            )
            deleted = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        return deleted

    def size(self) -> int:
        """Return the total number of entries currently stored (including expired)."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM cache").fetchone()
            return int(row["cnt"])

    def __repr__(self) -> str:
        return f"SQLiteCache(db={self.db_path!r}, default_ttl={self.default_ttl}s)"
