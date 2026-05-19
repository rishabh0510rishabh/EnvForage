# Contributing to EnvForge

First off, thank you for considering contributing to EnvForge! It's people like you that make this tool better for everyone.

Please read the [Code of Conduct](./CODE_OF_CONDUCT.md) to keep our community approachable and respectable.

## Development Setup

1. **Fork & Clone** the repository.
2. **Start Database**: We use Docker Compose for the PostgreSQL database.
   ```bash
   docker-compose up -d
   ```
3. **Install Dependencies**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   cd ..
   ```

4. **Install Pre-commit Hooks**:
   We recommend installing `pre-commit` globally so it works across all your projects and terminal sessions without needing to activate a virtual environment.
   ```bash
   # Recommended: Install globally
   pipx install pre-commit  # OR: pip install pre-commit
   
   # From the repo root, install the hooks
   pre-commit install
   ```
   > **Note**: If you prefer not to install it globally, you can use the version installed in `backend/.venv`, but you **must** ensure that virtual environment is active whenever you run `git commit`.

5. **Run Migrations & Seeds** (from `backend/`):
   ```bash
   cd backend
   alembic upgrade head
   python -m app.services.seed_service
   ```

## Folder Structure

```
EnvForge/
├── backend/            # FastAPI backend (API, Compatibility Engine, Templates)
├── cli/                # envforge-agent standalone CLI
├── docs/               # Architecture, ADRs, Workflows, Specs
├── .github/            # CI workflows, Issue Templates
└── docker-compose.yml
```

## How to Add Profiles

To add a new ML environment profile (e.g., JAX, TensorRT):
1. Review the [PROFILE_SPEC.md](./docs/PROFILE_SPEC.md) for the required schema.
2. Add your profile to `backend/seeds/profiles.yaml`.
3. Run the seed service (`python -m app.services.seed_service`) to test it locally.
4. Update `docs/FEATURES.md`.

## How to Add Templates

If you need a new output script format (e.g., `Makefile`):
1. Create the template in `backend/app/templates/jinja/`.
2. Register it in `TEMPLATE_MAP` inside `backend/app/templates/engine.py`.
3. Write a rendering test in `backend/tests/unit/templates/`.

## How to Test Scripts

We require high test coverage because generated scripts affect real systems.
- Run backend tests: `pytest tests/`
- Run CLI agent tests: `cd ../cli && pytest tests/`
- **Rule**: If you add a new CUDA version to the compatibility matrix, you *must* add a test case for it in `test_resolver.py`.

See [TESTING.md](./docs/TESTING.md) for more details.

## Pull Request Guidelines

1. Ensure all tests pass.
2. Ensure your code is formatted with `black` and `ruff`. (The pre-commit hooks installed in Step 4 will handle this automatically upon `git commit`).
3. Ensure type checking passes (`mypy app/`).
4. Update relevant documentation in the `docs/` folder.
5. Fill out the Pull Request template completely.

## Commit Style

We follow [Conventional Commits](https://www.conventionalcommits.org/).

Examples:
- `feat(api): add new profile endpoint`
- `fix(agent): handle missing WMI gracefully on Windows`
- `docs: update ROADMAP.md for phase 2`
- `test(core): add edge cases for CompatibilityResolver`

## Branching Strategy

- `main` is the primary development branch.
- Feature branches: `feat/your-feature-name`
- Bugfix branches: `fix/your-bug-name`

## Getting Help
If you need help, please open an issue with the `question` label, or check out [SUPPORT.md](./SUPPORT.md).
