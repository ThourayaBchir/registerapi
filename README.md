# User Activation API

Production-ready scaffold for a FastAPI registration and activation service backed by PostgreSQL, Redis, and Celery.

## Requirements

- Docker & Docker Compose (recommended for local development)
- Python 3.12+ with `uv` if you plan to run without containers

## Quick Start

### Docker Compose (recommended)

```bash
docker compose up --build
```

Containers expose:

- API: <http://localhost:8000>
- Scalar docs UI: <http://localhost:8000/docs>
- Mock email API: <http://localhost:8080/v1/send>
- PostgreSQL: `localhost:5432` (user/password: `register`)
- Redis: `localhost:6379`

Copy `.env.example` to `.env` before starting and adjust secrets as needed.

## Manual Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
TEST_DATABASE_URL=postgresql://register:register@localhost:5432/user_activation pytest
uvicorn app.main:app --reload
```

Before launching, copy `.env.example` to `.env`, update secrets, and run `python scripts/run_migrations.py` once to apply database schema changes. Ensure PostgreSQL/Redis are running locally (start them via `docker compose up -d postgres redis` or your preferred services manager).

## API Documentation

Scalar API reference is available at `/docs`. OpenAPI JSON is served at `/openapi.json` if you need to integrate with external tooling.

### Trying the API via `/docs`

1. Start the stack (Docker Compose or manual run).
2. Navigate to <http://localhost:8000/docs>.
3. Pick an endpoint, choose **Try it out**, and supply the payload.
4. For endpoints requiring Basic Auth (`/auth/resend`, `/auth/activate`), supply the email/password you used during registration.
5. Review the live response or copy the generated curl command for further testing.

## Project Structure

```
app/
  api/            # Route definitions and dependencies
  core/           # Configuration, DB pool, Redis, Celery
  services/       # Business logic orchestration
  repositories/   # Raw SQL data access
  tasks/          # Celery tasks
  utils/          # Helpers (e.g., email templates)
depoyment/
  Dockerfile      # Multi-stage build used by all services
tests/            # Unit, integration, and e2e tests
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

## Production Readiness

- **Configuration & Secrets** – All runtime settings originate from environment variables (see `.env.example`). For production, load them from your secret manager (e.g. AWS SSM, Azure Key Vault, HashiCorp Vault) rather than bundling a `.env` file. Rotate `SECRET_KEY`, database credentials, and Redis passwords regularly.
- **Database Migrations** – Before rolling out a release, run `python scripts/run_migrations.py` with the production `DATABASE_URL`. The runner executes each `*.sql` file in `app/db/migrations` in lexical order and exits cleanly if the schema is current.
- **Application & Worker Processes** – Launch the API with a production ASGI server (`uvicorn app.main:app --workers N --host 0.0.0.0 --port 8000`) managed by systemd/Supervisor/Kubernetes and fronted by a reverse proxy. Run the Celery worker separately (`celery -A app.core.celery_app.celery_app worker`) so background email dispatch stays decoupled from API traffic.
- **Email Delivery** – Point `EMAIL_API_URL` at your mail provider. Monitor Celery retries and provider responses; the bundled mock server is for local development only.
- **Redis & Rate Limiting** – Provision a managed Redis instance with persistence/high availability, since it powers both Celery (broker/result backend) and rate limiting. Tune thresholds in `app/core/constants.py` to match policy.
- **Observability & Health** – `/health/check` serves as a readiness probe. Ship API and worker logs to your observability stack and consider adding metrics/traces around activation attempts, rate limiting, and email dispatch.
- **Security Posture** – Passwords are hashed automatically via `passlib`. Enforce TLS end-to-end, align password complexity with your governance, and keep resend/activate flows protected by Basic Auth (credentials supplied via env vars).
- **Testing & CI** – The pytest suite covers repositories, services, Celery tasks, and API routes. In CI/CD, point `TEST_DATABASE_URL` to an ephemeral Postgres instance and run `pytest` before promoting builds.

## Testing

Set `TEST_DATABASE_URL` to a reachable Postgres instance (default points to `localhost:5432`). Then run:

```bash
source .venv/bin/activate
export TEST_DATABASE_URL=postgresql://register:register@localhost:5432/user_activation
pytest
```

Using Docker Compose, you can run tests inside the API container:

```bash
docker compose exec api pytest
```

## Code Quality

- Run `black .` to auto-format the codebase using `pyproject.toml` settings: `docker compose exec api black .`
- Run `ruff check .` to lint for style, correctness, and import issues: `docker compose exec api ruff check .`


## Maintenance Notes

- Celery broker/result backend default to the Redis URL defined in `.env`. Override with `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` if needed.
- Activation codes expire based on `ACTIVATION_CODE_TTL_SECONDS` (default 60 seconds) and are stored in PostgreSQL.
