# EnvForage — Database Schema Design

> **Version**: 1.0.0
> **Status**: Production
> **Last Updated**: 2026-05-21

---

## Design Principles

- All tables have `created_at` and `updated_at` timestamps (auto-managed)
- Soft deletes: `deleted_at` nullable timestamp (records are never hard-deleted)
- UUIDs for all primary keys (portable, avoids enumeration attacks)
- JSONB for flexible/extensible fields (avoids over-normalization for config data)
- Alembic for all schema migrations (no manual DDL in production)

---

## Entity Relationship Overview

```
environment_profiles
    │
    ├──< profile_packages (package list per profile)
    ├──< script_generation_jobs (generated script sets)
    │       └──< generated_scripts (individual files per job)
    │
cuda_compatibility_matrix
python_compatibility_matrix
    │
    └── (referenced by CompatibilityEngine in-memory, not FK'd)

diagnostic_reports
    │
    └──< verification_results
            └──< verification_checks

ai_sessions
    │
    └──< ai_suggestions
ai_audit_log
```

---

## Tables

### `environment_profiles`

```sql
CREATE TABLE environment_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(64) UNIQUE NOT NULL,  -- e.g. "pytorch-cuda"
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    tags            TEXT[],                        -- e.g. ["gpu", "deep-learning"]
    os_support      TEXT[],                        -- ["LINUX", "WSL", "WIN"]
    cuda_required   BOOLEAN NOT NULL DEFAULT FALSE,
    python_versions TEXT[] NOT NULL,               -- ["3.10", "3.11"]
    cuda_versions   TEXT[],                        -- ["11.8", "12.1"]
    status          VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE | DEPRECATED
    last_validated  DATE,
    metadata        JSONB,                         -- extensible extra fields
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
```

---

### `profile_packages`

```sql
CREATE TABLE profile_packages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES environment_profiles(id),
    package_name    VARCHAR(128) NOT NULL,         -- e.g. "torch"
    version_spec    VARCHAR(64) NOT NULL,           -- e.g. "2.1.0+cu118" or ">=2.0,<2.2"
    cuda_variant    VARCHAR(32),                    -- e.g. "cu118", "cu121", null for CPU
    is_optional     BOOLEAN NOT NULL DEFAULT FALSE,
    install_order   INT NOT NULL DEFAULT 0,         -- lower = install first
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_profile_packages_profile_id ON profile_packages(profile_id);
```

---

### `cuda_compatibility_matrix`

```sql
CREATE TABLE cuda_compatibility_matrix (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuda_version        VARCHAR(16) NOT NULL,       -- e.g. "12.1"
    min_driver_linux    VARCHAR(32),                -- e.g. "525.85.12"
    min_driver_windows  VARCHAR(32),                -- e.g. "528.33"
    cudnn_versions      TEXT[],                     -- ["8.9", "9.0"]
    supported_archs     TEXT[],                     -- ["sm_70", "sm_80", "sm_89"]
    notes               TEXT,
    source_url          TEXT,                       -- official docs URL
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cuda_version)
);
```

---

### `framework_version_matrix`

```sql
CREATE TABLE framework_version_matrix (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    framework           VARCHAR(64) NOT NULL,       -- e.g. "torch"
    version             VARCHAR(32) NOT NULL,       -- e.g. "2.1.0"
    min_python          VARCHAR(8) NOT NULL,        -- e.g. "3.8"
    max_python          VARCHAR(8) NOT NULL,        -- e.g. "3.11"
    supported_cuda      TEXT[],                     -- ["11.8", "12.1"]
    source_url          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (framework, version)
);
```

---

### `script_generation_jobs`

```sql
CREATE TABLE script_generation_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES environment_profiles(id),
    target_os       VARCHAR(16) NOT NULL,           -- "LINUX" | "WSL" | "WIN"
    python_version  VARCHAR(8) NOT NULL,
    cuda_version    VARCHAR(16),
    overrides       JSONB,                          -- user-specified version overrides
    status          VARCHAR(16) NOT NULL DEFAULT 'PENDING',  -- PENDING|RUNNING|DONE|FAILED
    error           TEXT,
    resolved_env    JSONB,                          -- final resolved version set
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
```

---

### `generated_scripts`

```sql
CREATE TABLE generated_scripts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID NOT NULL REFERENCES script_generation_jobs(id),
    filename    VARCHAR(128) NOT NULL,              -- e.g. "setup.sh"
    content     TEXT NOT NULL,
    size_bytes  INT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_generated_scripts_job_id ON generated_scripts(job_id);
```

---

### `diagnostic_reports`

```sql
CREATE TABLE diagnostic_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_data     JSONB NOT NULL,                -- Full DiagnosticReport JSON
    os_type         VARCHAR(16),                   -- "LINUX" | "WSL" | "WIN"
    gpu_name        VARCHAR(128),
    cuda_version    VARCHAR(16),
    python_version  VARCHAR(8),
    driver_version  VARCHAR(32),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### `verification_results`

```sql
CREATE TABLE verification_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID REFERENCES diagnostic_reports(id),
    profile_id      UUID NOT NULL REFERENCES environment_profiles(id),
    overall_status  VARCHAR(16) NOT NULL,           -- "PASSED" | "FAILED" | "PARTIAL"
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE verification_checks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id       UUID NOT NULL REFERENCES verification_results(id),
    check_name      VARCHAR(128) NOT NULL,
    passed          BOOLEAN NOT NULL,
    detail          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### `ai_sessions`

```sql
CREATE TABLE ai_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    diagnostic_id       UUID REFERENCES diagnostic_reports(id),
    verification_id     UUID REFERENCES verification_results(id),
    profile_id          UUID REFERENCES environment_profiles(id),
    provider            VARCHAR(32) NOT NULL,       -- "openai" | "openrouter" | "ollama"
    model               VARCHAR(64) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_suggestions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES ai_sessions(id),
    step_number     INT NOT NULL,
    title           VARCHAR(256) NOT NULL,
    description     TEXT NOT NULL,
    severity        VARCHAR(16) NOT NULL,           -- "CRITICAL" | "WARNING" | "INFO"
    safe_commands   TEXT[],
    template_id     VARCHAR(128),                   -- repair template ID if applicable
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### `ai_audit_log`

```sql
CREATE TABLE ai_audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID REFERENCES ai_sessions(id),
    input_hash          VARCHAR(64) NOT NULL,       -- SHA256 of input (not PII)
    safety_passed       BOOLEAN NOT NULL,
    safety_violation    TEXT,                       -- blocked pattern if failed
    provider            VARCHAR(32),
    tokens_used         INT,
    latency_ms          INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Index Strategy

```sql
-- Profile queries
CREATE INDEX idx_profiles_slug ON environment_profiles(slug);
CREATE INDEX idx_profiles_tags ON environment_profiles USING GIN(tags);
CREATE INDEX idx_profiles_os ON environment_profiles USING GIN(os_support);

-- Script job lookups
CREATE INDEX idx_jobs_profile_id ON script_generation_jobs(profile_id);
CREATE INDEX idx_jobs_status ON script_generation_jobs(status);

-- Diagnostic report queries
CREATE INDEX idx_diag_os ON diagnostic_reports(os_type);
CREATE INDEX idx_diag_cuda ON diagnostic_reports(cuda_version);

-- Audit log queries
CREATE INDEX idx_audit_session ON ai_audit_log(session_id);
CREATE INDEX idx_audit_safety ON ai_audit_log(safety_passed);
```

---

## Migration Strategy

- Tool: **Alembic** (SQLAlchemy migrations)
- All schema changes go through migrations — no manual DDL
- Migration files are numbered sequentially: `0001_initial.py`, `0002_add_profiles.py`
- Down migrations are implemented for every up migration (rollback support)
- Seed data goes in separate `seeds/` directory, not in migration files

---

## Data Lifecycle

| Table | Retention | Notes |
|-------|----------|-------|
| `environment_profiles` | Permanent | Soft-delete only |
| `script_generation_jobs` | 30 days | Cleanup job |
| `generated_scripts` | 7 days | Cleanup job |
| `diagnostic_reports` | 30 days | User data |
| `ai_sessions` | 90 days | Audit requirement |
| `ai_audit_log` | 1 year | Compliance |
