# ADR-005: YAML Fixtures for Seed Data with Idempotent Service

**Status**: Accepted
**Date**: 2026-05-06
**Author**: EnvForage — Phase 1 Implementation

---

## Context

The application needs initial profile data (6 environment profiles) and
compatibility matrices loaded into PostgreSQL on startup. Options for managing
this seed data include:

1. Hardcoded Python dicts in migration files
2. SQL `INSERT` statements in migration files
3. YAML fixture files loaded by a separate seed service
4. A seed Alembic migration

## Decision

Use YAML fixture files in `backend/seeds/` loaded by an idempotent Python
service (`app/services/seed_service.py`) that runs at container startup.

```
docker-compose up → alembic upgrade head → python -m app.services.seed_service → uvicorn
```

## Rationale

1. **Human-readable**: YAML is easy to read, diff, and review in PRs. Non-developer
   contributors (e.g., ML engineers adding a new profile) can edit YAML without
   touching Python.
2. **Idempotent**: The seed service checks `slug` uniqueness before inserting.
   Running it multiple times is safe — it skips already-existing records. No
   `IF NOT EXISTS` gymnastics in SQL.
3. **Separation from migrations**: Migrations handle schema; seeds handle data.
   Mixing them couples data concerns into schema history, making rollbacks complex.
4. **Version-controlled, reviewable data**: YAML files are diff-friendly. A PR
   that adds a profile is a readable, reviewable YAML change — not an opaque SQL string.

## Alternatives Considered

- **SQL INSERTs in migrations**: Rejected — couples data to schema history; rollback
  of schema can accidentally destroy seed data; SQL strings are not readable in PRs.
- **Hardcoded Python dicts**: Rejected — not contributor-friendly; requires Python
  knowledge to modify profiles; no separation of data from logic.
- **Alembic data migration**: Rejected for the same reasons as SQL INSERTs, with
  added coupling to migration versions.

## Tradeoffs

- Seed service must be explicitly run (handled in Docker Compose `command`).
- YAML parsing is slower than native Python dicts — acceptable for a startup task.
- YAML schema is not type-checked at load time. Mitigation: add a YAML schema
  validator (e.g., `pydantic` parse) in a future Phase 6 hardening step.

## File Structure

```
backend/
└── seeds/
    ├── profiles.yaml         # 6 environment profiles + packages
    └── cuda_matrix.yaml      # CUDA version → driver → cuDNN matrix
```

## Adding a New Profile (Contributor Guide)

1. Add a new entry to `seeds/profiles.yaml` following the existing format
2. Run `python -m app.services.seed_service` locally to load it
3. Verify it appears in `GET /api/v1/profiles`
4. Add a test in `tests/unit/compatibility/` for any new version combinations
5. Update `docs/FEATURES.md` profile table
