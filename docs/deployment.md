# EnvForage Deployment Guide

## Celery Worker

The diagnostic worker (`app.worker`) uses `asyncio.run()` internally to
fetch profiles from the async database session. This means:

- **You MUST use `--pool=prefork`** (the Celery default). Do NOT use
  `--pool=gevent` or `--pool=eventlet` — they patch the event loop and
  will cause `RuntimeError: This event loop is already running`.

- Start the worker with:

  ```bash
  celery -A app.worker worker --pool=prefork --loglevel=info
  ```

## Docker Compose (Production)

See `docker-compose.prod.yml`. Key features:

- **Caddy reverse proxy** handles TLS termination automatically via
  Let's Encrypt. Set the `DOMAIN` env var to your production domain.
- **Alembic migrations** run in a dedicated `migrate` service before
  the API starts (prevents race conditions with multiple workers).
- The API is **not directly exposed** — only ports 80/443 are open.

### Quick Start

```bash
# Set required environment variables
export DOMAIN=envforage.example.com
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_USER=envforage
export POSTGRES_PASSWORD=$(openssl rand -hex 16)
export POSTGRES_DB=envforage
export REDIS_PASSWORD=$(openssl rand -hex 16)
export ALLOWED_ORIGINS=https://envforage.example.com

# Launch
docker compose -f docker-compose.prod.yml up -d
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ prod | 32+ char secret for JWT signing |
| `DATABASE_URL` | ✅ | PostgreSQL async URL |
| `REDIS_URL` | ✅ prod | Redis URL for cache + rate limiting + Celery |
| `ALLOWED_ORIGINS` | ✅ prod | Comma-separated CORS origins |
| `DOMAIN` | ✅ prod | Domain for Caddy TLS (e.g., `envforage.example.com`) |
| `UPLOAD_DIR` | ❌ | Upload directory (default: `/tmp/envforage_uploads`) |
| `AWS_ACCESS_KEY_ID` | ❌ | S3 uploads (leave blank for local) |
| `AWS_SECRET_ACCESS_KEY` | ❌ | S3 uploads |
| `S3_BUCKET_NAME` | ❌ | S3 bucket name |
| `ENVFORAGE_LLM_PROVIDER` | ❌ | `ollama` or `openrouter` |
| `OPENROUTER_API_KEY` | ❌ | Only if using OpenRouter |
