# EduConnect AI

AI-powered multi-channel school engagement platform, built with FastAPI, PostgreSQL, Redis, and Celery.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Meta WhatsApp Cloud API credentials (for production)

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. Start all services

```bash
docker-compose up --build
```

This starts:
- **FastAPI API** at `http://localhost:8000`
- **Celery worker** for background message processing
- **Celery Beat** for scheduled tasks
- **PostgreSQL 16** on port 5432
- **Redis 7** on port 6379

Database migrations run automatically on startup.

### 3. Verify

- Health check: `GET http://localhost:8000/health`
- API docs (dev mode): `http://localhost:8000/docs`

### 4. Configure WhatsApp Webhook

In your Meta App Dashboard, set the webhook URL to:

```
https://your-domain.com/api/v1/whatsapp/webhook
```

Subscribe to the `messages` field. The verify token is your `WA_VERIFY_TOKEN` from `.env`.

## Project Structure

```
app/
  main.py              # FastAPI entry point
  config.py            # Settings via pydantic-settings
  database.py          # SQLAlchemy async engine
  models/              # ORM models
  schemas/             # Pydantic request/response schemas
  api/v1/              # Route handlers
  services/            # Business logic
  flows/               # WhatsApp conversation flows
  tasks/               # Celery background tasks
  utils/               # Helpers (signatures, message builders)
  middleware/          # Rate limiting, audit logging
```

## Development

### Run without Docker

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Run tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## Architecture

See `Edpassare-Technical-Architecture.md` for the full specification.
