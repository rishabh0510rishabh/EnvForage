# ADR-006: SQLite In-Memory Database for Unit Tests

**Status**: Accepted
**Date**: 2026-05-06
**Author**: EnvForage — Phase 1 Implementation

---

## Context

The backend needs a test database strategy for unit tests. The options are:

1. **Real PostgreSQL** (Docker container in CI/CD or local)
2. **SQLite in-memory** via `aiosqlite`
3. **No database** (mock all DB calls)

## Decision

Use SQLite in-memory (via `aiosqlite`) for all unit tests. Integration tests
(in `tests/integration/`) may use a real PostgreSQL instance.

```python
# conftest.py
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ...
```

## Rationale

1. **Zero external dependencies**: Unit tests run with `pytest` alone — no Docker,
   no Postgres service, no environment setup. CI runs faster and is simpler.
2. **Isolation**: Each test gets a fresh in-memory DB, destroyed after the test.
   No state leaks between tests.
3. **Fast**: SQLite in-memory is significantly faster than Postgres for small
   test fixtures.
4. **Compatible**: SQLAlchemy's async API works identically with SQLite
   and PostgreSQL for standard ORM operations.

## Alternatives Considered

- **Real PostgreSQL**: Rejected for unit tests — requires Docker or Postgres
  install; slow CI; complex fixture management. Reserved for integration tests.
- **Mocking all DB calls**: Rejected — mocks tightly couple tests to implementation
  details; changes to queries break tests for wrong reasons.

## Tradeoffs

- SQLite does not support PostgreSQL-specific types used in production:
  `ARRAY`, `JSONB`, `UUID(as_uuid=True)`.
  These are used in ORM models for Postgres but not yet exercised in unit tests.
  Integration tests against real PostgreSQL are needed to cover these types.
- Some PostgreSQL-specific query features (e.g., GIN index queries, `ARRAY` operators)
  cannot be tested with SQLite.

## Boundary

| Test Type | Database | Location |
|-----------|----------|----------|
| Unit tests (pure logic, resolver, safety) | None — no DB | `tests/unit/` |
| Unit tests (service layer with ORM) | SQLite in-memory | `tests/unit/` |
| Integration tests (full API stack) | PostgreSQL (Docker) | `tests/integration/` |
