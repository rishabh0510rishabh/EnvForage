from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_db(rowcount: int = 3):
    result = MagicMock()
    result.rowcount = rowcount
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_session_cm(db):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


async def test_success_sets_last_run_success_to_1():
    from app.services import cleanup_service

    db = _make_db()
    with patch("app.services.cleanup_service.AsyncSessionLocal", return_value=_make_session_cm(db)):
        await cleanup_service.run_cleanup()

    assert cleanup_service.CLEANUP_LAST_RUN_SUCCESS._value.get() == 1.0


async def test_failure_sets_last_run_success_to_0():
    from app.services import cleanup_service

    db = _make_db()
    db.execute = AsyncMock(side_effect=Exception("DB connection lost"))
    with patch("app.services.cleanup_service.AsyncSessionLocal", return_value=_make_session_cm(db)):
        with pytest.raises(Exception):
            await cleanup_service.run_cleanup()

    assert cleanup_service.CLEANUP_LAST_RUN_SUCCESS._value.get() == 0.0


async def test_failure_reraises_exception():
    from app.services import cleanup_service

    db = _make_db()
    db.execute = AsyncMock(side_effect=RuntimeError("disk full"))
    with patch("app.services.cleanup_service.AsyncSessionLocal", return_value=_make_session_cm(db)):
        with pytest.raises(RuntimeError, match="disk full"):
            await cleanup_service.run_cleanup()


async def test_rollback_called_on_failure():
    from app.services import cleanup_service

    db = _make_db()
    db.execute = AsyncMock(side_effect=Exception("error"))
    with patch("app.services.cleanup_service.AsyncSessionLocal", return_value=_make_session_cm(db)):
        with pytest.raises(Exception):
            await cleanup_service.run_cleanup()

    db.rollback.assert_awaited_once()
