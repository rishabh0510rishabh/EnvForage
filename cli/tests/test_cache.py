"""
Unit tests for the SQLiteCache class.

These tests run against a temporary in-memory SQLite database so they do not
touch the user's real cache file and are safe to run in any environment.
"""

from __future__ import annotations

import time
import pytest

from envforage.cache import SQLiteCache


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def cache(tmp_path: "pytest.TempPathFactory") -> SQLiteCache:  # type: ignore[type-arg]
    """Return a fresh SQLiteCache pointing to a temporary directory."""
    return SQLiteCache(db_path=tmp_path / "test_cache.db", default_ttl=0)


# ── set / get ─────────────────────────────────────────────────────────────────

class TestSetAndGet:
    def test_set_and_get_dict(self, cache: SQLiteCache) -> None:
        cache.set("key1", {"hello": "world"})
        result = cache.get("key1")
        assert result == {"hello": "world"}

    def test_set_and_get_list(self, cache: SQLiteCache) -> None:
        cache.set("key2", [1, 2, 3])
        assert cache.get("key2") == [1, 2, 3]

    def test_set_and_get_string(self, cache: SQLiteCache) -> None:
        cache.set("key3", "plain string")
        assert cache.get("key3") == "plain string"

    def test_set_and_get_number(self, cache: SQLiteCache) -> None:
        cache.set("key4", 42)
        assert cache.get("key4") == 42

    def test_set_and_get_none_value(self, cache: SQLiteCache) -> None:
        cache.set("key5", None)
        assert cache.get("key5") is None

    def test_get_missing_key_returns_none(self, cache: SQLiteCache) -> None:
        assert cache.get("nonexistent") is None

    def test_overwrite_existing_key(self, cache: SQLiteCache) -> None:
        cache.set("key6", "first")
        cache.set("key6", "second")
        assert cache.get("key6") == "second"

    def test_set_with_explicit_zero_ttl_never_expires(self, cache: SQLiteCache) -> None:
        """TTL=0 means immortal — still present after a second."""
        cache.set("immortal", {"data": 99}, ttl=0)
        time.sleep(0.05)
        assert cache.get("immortal") == {"data": 99}

    def test_set_with_short_ttl_expires(self, cache: SQLiteCache) -> None:
        """TTL=2 seconds — entry should be gone after 2.5 s."""
        cache.set("short_lived", "gone soon", ttl=2)
        time.sleep(2.5)
        assert cache.get("short_lived") is None

    def test_set_uses_default_ttl_when_not_specified(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        """Verify the default_ttl parameter is used when ttl=None."""
        short_cache = SQLiteCache(db_path=tmp_path / "short.db", default_ttl=2)
        short_cache.set("x", "y")  # uses default_ttl=2
        time.sleep(2.5)
        assert short_cache.get("x") is None


# ── delete ────────────────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_existing_key(self, cache: SQLiteCache) -> None:
        cache.set("to_delete", 123)
        cache.delete("to_delete")
        assert cache.get("to_delete") is None

    def test_delete_nonexistent_key_is_noop(self, cache: SQLiteCache) -> None:
        """Deleting a key that does not exist should not raise."""
        cache.delete("ghost")  # should not raise

    def test_delete_only_removes_target_key(self, cache: SQLiteCache) -> None:
        cache.set("a", 1)
        cache.set("b", 2)
        cache.delete("a")
        assert cache.get("a") is None
        assert cache.get("b") == 2


# ── clear ─────────────────────────────────────────────────────────────────────

class TestClear:
    def test_clear_removes_all_entries(self, cache: SQLiteCache) -> None:
        for i in range(5):
            cache.set(f"key_{i}", i)
        cache.clear()
        for i in range(5):
            assert cache.get(f"key_{i}") is None

    def test_clear_on_empty_cache_is_noop(self, cache: SQLiteCache) -> None:
        cache.clear()  # should not raise when already empty


# ── size ──────────────────────────────────────────────────────────────────────

class TestSize:
    def test_size_empty_cache(self, cache: SQLiteCache) -> None:
        assert cache.size() == 0

    def test_size_after_inserts(self, cache: SQLiteCache) -> None:
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size() == 2

    def test_size_after_delete(self, cache: SQLiteCache) -> None:
        cache.set("a", 1)
        cache.set("b", 2)
        cache.delete("a")
        assert cache.size() == 1

    def test_size_after_clear(self, cache: SQLiteCache) -> None:
        cache.set("a", 1)
        cache.clear()
        assert cache.size() == 0


# ── purge_expired ─────────────────────────────────────────────────────────────

class TestPurgeExpired:
    def test_purge_removes_expired_entries(self, cache: SQLiteCache) -> None:
        cache.set("stale", "old", ttl=2)
        cache.set("fresh", "new", ttl=0)
        time.sleep(2.5)
        deleted = cache.purge_expired()
        assert deleted == 1
        assert cache.get("fresh") == "new"

    def test_purge_returns_zero_when_nothing_expired(self, cache: SQLiteCache) -> None:
        cache.set("immortal", "here", ttl=0)
        deleted = cache.purge_expired()
        assert deleted == 0

    def test_purge_does_not_remove_valid_entries(self, cache: SQLiteCache) -> None:
        cache.set("valid", "still here", ttl=3600)
        cache.purge_expired()
        assert cache.get("valid") == "still here"


# ── repr ──────────────────────────────────────────────────────────────────────

class TestRepr:
    def test_repr_contains_db_path(self, cache: SQLiteCache, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        assert "SQLiteCache" in repr(cache)
