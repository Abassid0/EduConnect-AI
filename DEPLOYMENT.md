# EduConnect AI — Production Deployment Guide

## Prerequisites

- Docker & Docker Compose v2
- Domain with HTTPS (required for WhatsApp webhooks)
- Meta Business account with WhatsApp Business API access
- Paystack account (live keys)
- Anthropic API key
- PostgreSQL 16+ (managed or containerised)
- Redis 7+ (managed or containerised)

## Environment Variables

Create a `.env` file from this template. **All values are required in production.**

```env
# --- Core ---
APP_ENV=production
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
DEBUG=false

# --- Database ---
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/educonnect

# --- Redis ---
REDIS_URL=redis://<host>:6379/0

# --- WhatsApp Business API ---
WA_PHONE_NUMBER_ID=<from Meta dashboard>
WA_BUSINESS_ACCOUNT_ID=<from Meta dashboard>
WA_ACCESS_TOKEN=<permanent system user token>
WA_VERIFY_TOKEN=<random string you choose — must match Meta webhook config>
WA_APP_SECRET=<from Meta App Settings → Basic → App Secret>
WA_API_VERSION=v21.0

# --- Paystack ---
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_PUBLIC_KEY=pk_live_...
PAYSTACK_CALLBACK_URL=https://your-domain.com/payment/callback

# --- AI (Anthropic) ---
ANTHROPIC_API_KEY=sk-ant-...

# --- CORS ---
CORS_ORIGINS=https://admin.your-domain.com

# --- AWS (receipt storage) ---
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=educonnect-receipts
AWS_REGION=eu-west-1
```

## Option A: Railway Deployment

### 1. Create services

```bash
railway login
railway init
```

Create three Railway services from the same repo:
- **api** — the FastAPI app
- **worker** — Celery worker
- **beat** — Celery beat scheduler

Add managed PostgreSQL and Redis plugins via the Railway dashboard.

### 2. Configure each service

**api** start command:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

**worker** start command:
```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

**beat** start command:
```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

### 3. Set environment variables

Copy all `.env` values to Railway's Variables tab for each service. Railway auto-provides `DATABASE_URL` and `REDIS_URL` from plugins — map them or set manually.

### 4. Deploy

```bash
railway up
```

### 5. Configure Meta webhook

Set the webhook URL in Meta Developer Console:
```
https://<your-railway-domain>/api/v1/whatsapp/webhook
```

Set the verify token to match `WA_VERIFY_TOKEN`.

Subscribe to: `messages`, `message_deliveries`, `message_reads`.

## Option B: AWS (ECS + Fargate)

### 1. Build and push Docker image

```bash
aws ecr create-repository --repository-name educonnect
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

docker build -t educonnect .
docker tag educonnect:latest <account>.dkr.ecr.<region>.amazonaws.com/educonnect:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/educonnect:latest
```

### 2. Infrastructure

Create the following AWS resources:
- **RDS PostgreSQL 16** — db.t3.micro minimum, enable encryption at rest
- **ElastiCache Redis 7** — cache.t3.micro minimum
- **ECS Cluster** with 3 Fargate services:
  - `api` (port 8000, ALB target group)
  - `worker` (no port exposure)
  - `beat` (no port exposure)
- **ALB** with HTTPS listener (ACM certificate)
- **Secrets Manager** for all environment variables

### 3. Task definitions

Each service uses the same Docker image with different commands:

| Service | Command | CPU | Memory |
|---------|---------|-----|--------|
| api | `sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"` | 512 | 1024 |
| worker | `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2` | 256 | 512 |
| beat | `celery -A app.tasks.celery_app beat --loglevel=info` | 256 | 256 |

### 4. ALB Health check

Path: `/health`
Expected: HTTP 200, body contains `"status":"healthy"`

## Option C: Docker Compose (VPS)

### 1. Provision a VPS

Ubuntu 22.04+, minimum 2 vCPU / 4 GB RAM.

### 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 3. Clone and configure

```bash
git clone <your-repo> /opt/educonnect
cd /opt/educonnect
cp .env.example .env
# Edit .env with production values
```

### 4. Production docker-compose override

Create `docker-compose.prod.yml`:

```yaml
version: "3.9"
services:
  api:
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"
    restart: always
    volumes: []

  worker:
    restart: always

  beat:
    restart: always

  db:
    restart: always

  redis:
    restart: always
```

### 5. Start services

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 6. HTTPS via Nginx + Certbot

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Nginx config:
```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Post-Deployment Checklist

- [ ] `/health` returns `{"status":"healthy"}` with all checks passing
- [ ] WhatsApp webhook verification succeeds in Meta dashboard
- [ ] Send a test WhatsApp message — confirm bot responds
- [ ] Test payment flow end-to-end with Paystack test card
- [ ] Admin dashboard loads and login works
- [ ] Celery worker processes background tasks (check logs)
- [ ] Celery beat fires scheduled reminders
- [ ] AI assistant responds to natural language queries
- [ ] Confirm `WA_APP_SECRET` is set (webhook rejects requests without it)
- [ ] `SECRET_KEY` is not the default `change-me`
- [ ] `DEBUG=false` in production
- [ ] CORS origins restricted to admin dashboard domain
- [ ] Database backups configured (daily minimum)
- [ ] Log aggregation set up (CloudWatch, Papertrail, or similar)

## Database Migrations

Migrations run automatically on API startup via `alembic upgrade head`. To run manually:

```bash
docker compose exec api alembic upgrade head
```

To create a new migration after model changes:

```bash
docker compose exec api alembic revision --autogenerate -m "description"
```

## Creating the First Admin User

After deployment, create the initial super_admin via the API. Since the `/auth/register` endpoint requires super_admin auth, use the management script:

```bash
docker compose exec api python -c "
import asyncio, uuid, bcrypt
from app.database import async_session_factory
from app.models.admin_user import AdminUser

async def create():
    async with async_session_factory() as db:
        user = AdminUser(
            id=uuid.uuid4(),
            email='admin@educonnect.ng',
            full_name='Admin',
            hashed_password=bcrypt.hashpw(b'CHANGE-THIS-PASSWORD', bcrypt.gensalt()).decode(),
            role='super_admin',
        )
        db.add(user)
        await db.commit()
        print(f'Created admin: {user.email}')

asyncio.run(create())
"
```

Change the password immediately after first login.

## Monitoring

- **Health endpoint**: `GET /health` — checks database, Redis, and WhatsApp API connectivity
- **Logs**: Structured with correlation IDs (`X-Request-ID` header); each request logged with `[correlation_id] METHOD /path status duration`
- **Metrics to watch**: response time p95, error rate, webhook processing latency, AI confidence scores, escalation rate
