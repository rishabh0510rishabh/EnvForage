# Testing Strategy

Because EnvForage generates executable scripts that modify system configurations, testing is not optional — it is a strict requirement for all contributions.

Our test suite is divided into three tiers:

## 1. Unit Tests (Backend)

Located in `backend/tests/unit/`. These tests execute without any external dependencies (no PostgreSQL instance, no network access). They use an in-memory SQLite database (`aiosqlite`) via fixtures.

**Key Focus Areas:**
- **Compatibility Engine**: `test_resolver.py` is the most important test file in the project. It tests the pure-Python deterministic version matrix. Every time a new CUDA version or framework version is added, a corresponding test must be added here.
- **Safety Filter**: `test_safety.py` asserts that dangerous shell strings (like `rm -rf /`) raise a `SafetyViolationError`. Any new forbidden pattern must have a test case.
- **Template Rendering**: Tests ensure that Jinja2 templates render cleanly without missing variables (thanks to `StrictUndefined`).

**Run them:**
```bash
cd backend
pytest tests/unit/ --cov=app --cov-report=term-missing
```

## 2. Unit Tests (CLI Agent)

Located in `cli/tests/`. The `envforage` must be tested across different operating systems. Since CI runners don't have multiple GPUs, we use **JSON Fixtures**.

**JSON Fixtures (`cli/tests/fixtures/`)**:
We capture real `DiagnosticReport` outputs from actual hardware (Linux GPU, WSL2, Windows GPU) and save them as JSON. The test suite loads these JSON files to test the Pydantic schemas and the `ReportBuilder` without needing actual NVIDIA hardware.

**Run them:**
```bash
cd cli
pytest tests/
```

## 3. Integration Tests

Located in `backend/tests/integration/`. These tests require the Docker Compose stack to be running (specifically the PostgreSQL database). 

**Key Focus Areas:**
- **API Endpoints**: Validates `GET /profiles`, `POST /scripts/generate`, and `POST /diagnose`.
- **Database Migrations**: Ensures Alembic migrations execute cleanly against a real Postgres instance.

**Run them:**
```bash
cd backend
pytest tests/integration/
```

## 4. Environment Testing (Manual / Sandboxed)

Before a new profile (e.g., `pytorch-cuda`) is marked as `ACTIVE` in `seeds/profiles.yaml`, the generated scripts must be executed in a real environment to ensure they successfully provision a working ML environment.

**How to verify:**
1. Generate the `setup.sh` and `verify_torch.sh` scripts for the profile.
2. Run `setup.sh` inside a fresh WSL2 instance or Ubuntu Docker container.
3. Run `verify_torch.sh` and ensure it outputs `PASS` for all checks (CUDA availability, tensor creation).
