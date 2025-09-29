# User Activation API

Production-ready scaffold for a FastAPI registration and activation service backed by PostgreSQL, Redis, and Celery.

## Requirements

- Docker & Docker Compose (recommended for local development)
- Python 3.12+ with `uv` if you plan to run without containers

## Quick Start

### Docker Compose

1. Start the stack:

```bash
docker compose up --build -d
```

2. Run migrations:
```bash
docker compose exec api python -m app.scripts.run_migrations
```
3. Try it out:
```bash
http://localhost:8000/docs
```
4. Try it with curl:
```bash
curl http://localhost:8000/auth/register \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
  "email": "abc@abc.com",
  "password": "Abcdefg@0"
}'

```

Containers expose:

- API: <http://localhost:8000>
- Scalar docs UI: <http://localhost:8000/docs>
- Mock email API: <http://localhost:8080>
- PostgreSQL: `localhost:5432` (user/password: `register`)
- Redis: `localhost:6379`
To verify migrations ran:
```bash
docker compose exec postgres psql \
  -U register \
  -d user_activation \
  -c '\\dt'
```

## API Documentation

Scalar API reference is available at `/docs`. OpenAPI JSON is served at `/openapi.json` if needed to integrate with external tooling.

### Trying the API via `/docs`

1. Start the stack (Docker Compose).
2. Navigate to <http://localhost:8000/docs>.
3. Pick an endpoint, choose **Try it out**, and supply the payload.
4. For endpoints requiring Basic Auth (`/auth/resend`, `/auth/activate`).

## Project Structure

```
app/
  api/            # Route definitions and dependencies
  core/           # Configuration, DB pool, Redis, Celery
  services/       # Business logic orchestration
  repositories/   # Raw SQL data access
  tasks/          # Celery tasks
  utils/          # Helpers (e.g., email templates)
  tests/          # Unit, integration, and e2e tests
  scripts/        # Utility scripts
depoyment/
  Dockerfile      # Multi-stage build used by all services

```

## Architecture Overview

<img src="arch.png" alt="Architecture diagram" width="600" />

- **Presentation layer** – FastAPI routers in `app/api/routes/` expose health and auth endpoints, wired via dependencies in `app/api/deps.py`.
- **Service layer** – `app/services/` hosts the business workflows for registration, activation, rate limiting, and email dispatch.
- **Data layer** – Repositories under `app/repositories/` encapsulate PostgreSQL access, paired with SQL migrations in `app/db/migrations`; Redis helpers live in `app/core/redis.py` and `app/services/rate_limiter.py`.
- **Background tasks** – Celery configuration (`app/core/celery_app.py`) plus tasks (`app/tasks/email.py`) push activation emails asynchronously.
- **Cross-cutting** – Configuration, security, and utilities are grouped in `app/core/` and `app/utils/`.

## Logic Flow

1. **Register** – `/auth/register` validates `UserCreate`, hashes the password, persists a new user, creates an activation code, and enqueues an email.
2. **Resend** – `/auth/resend` authenticates via Basic Auth, enforces Redis-based rate limits, issues a fresh code, and sends another email.
3. **Activate** – `/auth/activate` checks the submitted code, activates the user on success, resets rate limits, or records failures for lockout.
4. **Email dispatch** – Celery workers execute `send_activation_email`, render templates, and POST to `EMAIL_API_URL` with retries.

## For Production

- **Application & Worker Processes** – Launch the API with a production ASGI server (`uvicorn app.main:app --workers N --host 0.0.0.0 --port 8000`) managed by systemd/Supervisor/Kubernetes and fronted by a reverse proxy. Run the Celery worker separately (`celery -A app.core.celery_app.celery_app worker`) so background email dispatch stays decoupled from API traffic.
- **Health** – `/health/check` serves as a readiness probe. 

## Running tests


```bash
docker compose exec api pytest ./app/tests


```


## Code Quality

- Run `black .` to auto-format the codebase using `pyproject.toml` settings: 

```bash
docker compose exec api black .
```
- Run `ruff check .` to lint for style, correctness, and import issues: 
```bash
docker compose exec api ruff check .
```


## Maintenance Notes

- Celery broker/result backend default to the Redis URL defined in `.env`. Override with `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` if needed.
- Activation codes expire based on `ACTIVATION_CODE_TTL_SECONDS` (default 60 seconds) and are stored in PostgreSQL.


## Clean All

```bash
docker compose down --volumes --remove-orphans --rmi local
```
