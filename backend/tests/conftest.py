"""Pytest configuration and shared fixtures."""

import json
import os

# Provide safe defaults for required settings BEFORE any `app.*` import,
# so module-level `get_settings()` calls (e.g. app.middleware.rate_limit)
# don't fail on missing SECRET_KEY / DATABASE_URL when tests run without a .env.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-in-prod")
# Use a postgres-format URL so app.database can construct its module-level
# engine with pool_size/max_overflow (postgres-only kwargs). The engine is
# lazy — it never connects. Tests open their own in-memory SQLite engine
# in the db_session fixture below.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
# Provide a deterministic admin key for tests so require_admin dependency
# does not return 503 (unconfigured) during the test suite.
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-for-ci")
import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import BinaryExpression

from app.database import Base


# 1. Compile postgresql.ARRAY and JSONB to TEXT/JSON on SQLite
@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# Compile containment operator (@>) for SQLite
@compiles(BinaryExpression, "sqlite")
def compile_binary_sqlite(element, compiler, **kw):
    operator = element.operator
    op_str = getattr(operator, "opstring", "")
    if op_str == "@>":
        left_type = element.left.type
        if hasattr(left_type, "item_type"):
            left = compiler.process(element.left, **kw)
            right = compiler.process(element.right, **kw)
            return f"array_contains({left}, {right})"
    return compiler.visit_binary(element, **kw)


# 2. Monkeypatch bind/result processors of postgresql.ARRAY for SQLite
_orig_bind_processor = ARRAY.bind_processor
_orig_result_processor = ARRAY.result_processor


def new_bind_processor(self, dialect):
    if dialect.name == "sqlite":

        def process(value):
            if value is None:
                return None
            return json.dumps(value)

        return process
    return _orig_bind_processor(self, dialect)


def new_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":

        def process(value):
            if value is None:
                return None
            try:
                return json.loads(value)
            except Exception as e:
                import logging
                logging.error(f"Test fixture error: {e}")
                return value

        return process
    return _orig_result_processor(self, dialect, coltype)


ARRAY.bind_processor = new_bind_processor  # type: ignore[method-assign]
ARRAY.result_processor = new_result_processor  # type: ignore[method-assign]

# Use in-memory SQLite for unit tests (no Postgres needed)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy for pytest-asyncio."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
async def test_engine():
    """Provide a session-scoped async SQLite engine using StaticPool."""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def register_sqlite_functions(dbapi_connection, connection_record):
        def array_contains(arr_str, item_str):
            if not arr_str or not item_str:
                return False
            try:
                arr = json.loads(arr_str)
                try:
                    item = json.loads(item_str)
                except Exception as e:
                    import logging
                    logging.error(f"Test fixture error: {e}")
                    item = item_str

                if isinstance(item, list):
                    return all(x in arr for x in item)
                return item in arr
            except Exception as e:
                import logging
                logging.error(f"Test fixture error: {e}")
                return False

        dbapi_connection.create_function("array_contains", 2, array_contains)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Provide a test database session backed by the shared in-memory SQLite engine."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def db_session_factory(test_engine):
    """Provide the session factory for per-request session creation using the shared SQLite engine."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield session_factory
