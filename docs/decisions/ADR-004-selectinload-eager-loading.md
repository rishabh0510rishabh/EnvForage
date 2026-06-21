# ADR-004: SQLAlchemy selectinload for Relationship Eager Loading

**Status**: Accepted
**Date**: 2026-05-06
**Author**: EnvForage — Phase 1 Implementation

---

## Context

SQLAlchemy ORM models with relationships (e.g., `EnvironmentProfile` → `ProfilePackage`)
need a loading strategy when accessed via async sessions. Options are:

1. **Lazy loading**: Load related objects on attribute access
2. **Joined loading** (`joinedload`): Single SQL JOIN query
3. **Subquery loading** (`subqueryload`): Separate subquery
4. **Select-in loading** (`selectinload`): Separate IN query per relationship

## Decision

Use `selectinload` for all eager loading of relationships in async context.

```python
# Example from profile_service.py
result = await db.execute(
    select(EnvironmentProfile)
    .options(selectinload(EnvironmentProfile.packages))
)
```

## Rationale

1. **Async compatibility**: `selectinload` is the only SQLAlchemy loading strategy that
   works correctly with `AsyncSession`. Lazy loading raises `MissingGreenlet` in async
   context because it attempts implicit I/O.
2. **N+1 prevention**: Explicitly declaring eager loading at the query level prevents
   accidental N+1 queries as the codebase grows.
3. **Predictable performance**: `selectinload` issues one additional `IN` query per
   relationship — predictable and cacheable.

## Alternatives Considered

- **Lazy loading**: Rejected — incompatible with `AsyncSession`; raises `MissingGreenlet`
  when relationship is accessed outside an active async context.
- **`joinedload`**: Rejected for one-to-many relationships — produces duplicate parent
  rows in results and requires `unique()` call; `selectinload` is simpler and avoids
  this footgun for collections.
- **`raiseload`** (default + explicit): Rejected — too verbose; would require explicit
  load strategy on every query.

## Tradeoffs

- Adds one extra SQL query per relationship eagerly loaded.
- For deeply nested relationships (3+ levels), multiple extra queries add up.
  Mitigation: keep query depth shallow; use service layer to compose data rather than
  deep ORM nesting.

## Rule for Contributors

> All queries that access ORM relationships **must** declare the loading strategy
> explicitly using `selectinload`. Never rely on lazy loading in async handlers.
