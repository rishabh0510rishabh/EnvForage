"""Unit tests for the require_admin dependency in app.api.deps."""

import os

import pytest
from fastapi import HTTPException

from app.api.deps import require_admin

# The test suite conftest.py sets ADMIN_API_KEY to this value.
_VALID_KEY = os.environ.get("ADMIN_API_KEY", "test-admin-key-for-ci")


class TestRequireAdmin:
    """Covers all branches of require_admin: valid key, missing key, wrong key, unconfigured."""

    async def test_valid_key_passes(self):
        """A matching key should return None without raising."""
        result = await require_admin(x_admin_api_key=_VALID_KEY)
        assert result is None

    async def test_missing_key_raises_401(self):
        """Absent header (None) must raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_api_key=None)
        assert exc_info.value.status_code == 401

    async def test_wrong_key_raises_401(self):
        """An incorrect key must raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_api_key="completely-wrong-key")
        assert exc_info.value.status_code == 401

    async def test_empty_key_raises_401(self):
        """An empty string key must be rejected with 401."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_api_key="")
        assert exc_info.value.status_code == 401

    async def test_www_authenticate_header_on_failure(self):
        """The 401 response must include the WWW-Authenticate header."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_api_key=None)
        assert "WWW-Authenticate" in exc_info.value.headers

    async def test_unconfigured_key_raises_503(self, monkeypatch):
        """When ADMIN_API_KEY is not configured the server must return 503."""
        monkeypatch.setenv("ADMIN_API_KEY", "")
        # Bust the lru_cache so get_settings() re-reads the env.
        from app.config import get_settings

        get_settings.cache_clear()
        try:
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(x_admin_api_key="any-key")
            assert exc_info.value.status_code == 503
        finally:
            # Restore so subsequent tests are not affected.
            get_settings.cache_clear()

    async def test_partial_key_prefix_raises_401(self):
        """A key that is a prefix of the correct key must not pass."""
        partial = _VALID_KEY[:4] if len(_VALID_KEY) > 4 else _VALID_KEY + "x"
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(x_admin_api_key=partial)
        assert exc_info.value.status_code == 401
