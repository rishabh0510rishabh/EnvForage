.PHONY: test lint run-dev db-upgrade clean

# Run backend tests
test:
		cd backend && pytest tests/

# Format and lint backend code
lint:
		cd backend && black . && ruff check .

# Start the FastAPI backend server
run-dev:
		cd backend && uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload

# Run database migrations and seed development data
db-upgrade:
		cd backend && alembic upgrade head && python -m app.services.seed_service

# Remove locally generated artifacts (caches, test outputs, build dirs)
clean:
		python scripts/clean.py