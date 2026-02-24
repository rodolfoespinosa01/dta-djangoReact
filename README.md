# DTA - Django + React (Development)

DTA is a Django + React nutrition platform for:
- B2C (direct clients)
- B2B (admin/coaches)
- B2B2C (admin-branded client signup flows)

This repository is **actively in development**.

## Current Status

- Admin Stripe signup and billing flows are in development
- Client meal-plan generation pipeline is in development
- Premium coaching plan architecture is in development
- Discount code support is in development (client/end-user and admin models)
- AI recipe idea generation exists as a **development feature only**

## AI Feature Status (Important)

AI recipe suggestions are **not a finalized production feature** yet.

Current state:
- MVP endpoint + UI exists for recipe ideas after meal generation
- Mock mode works for development/testing
- Optional OpenAI API integration is supported if a backend API key is configured
- Output quality, pricing controls, and production hardening are still in progress

ChatGPT Plus does **not** provide API credits for backend integration. OpenAI API usage requires a separate API key/billing setup.

## Tech Stack

- Backend: Django + Django REST Framework
- Frontend: React (CRA)
- Database: PostgreSQL
- Auth: JWT
- Payments: Stripe
- Queueing: Celery + Redis
- Local Dev HTTPS: React HTTPS + optional Django HTTPS via `uvicorn` + `mkcert`

## Local Setup (Recommended)

### Prerequisites (macOS)

```bash
brew install redis postgresql mkcert nss
brew services start redis
brew services start postgresql
mkcert -install
```

### Python / Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

### Frontend

```bash
cd frontend
npm install
```

## Local HTTPS Setup (to avoid browser "Not Secure" warnings)

Create trusted local certs in the repo root (works for `localhost` and `*.lvh.me`):

```bash
mkdir -p .certs
mkcert -key-file .certs/localhost-key.pem -cert-file .certs/localhost.pem localhost 127.0.0.1 ::1 lvh.me "*.lvh.me"
```

Notes:
- VS Code tasks are configured to use these certs automatically if present
- React runs on HTTPS
- Django task uses `uvicorn` HTTPS when available, otherwise falls back to `runserver`

## VS Code Tasks (Current)

Available tasks include:
- `Start All Services`
- `Kill All Services`
- `Reset All`
- `Full Reset DB`

Behavior:
- `Run Redis Server` is idempotent (won't fail if Redis is already running on `:6379`)
- `Kill All Services` attempts to stop local Django/React/Celery/Stripe CLI/Redis dev processes

## Running the App

Use your VS Code tasks (recommended), or run manually.

### Manual (example)

Backend (HTTPS via `uvicorn`, if installed):
```bash
cd backend
source venv/bin/activate
uvicorn core.asgi:application --host 0.0.0.0 --port 8000 --ssl-keyfile ../.certs/localhost-key.pem --ssl-certfile ../.certs/localhost.pem
```

Frontend:
```bash
cd frontend
HTTPS=true npm start
```

Celery worker:
```bash
cd backend
source venv/bin/activate
celery -A core worker -l info
```

Stripe webhook listener (client flow example):
```bash
stripe listen --forward-to https://localhost:8000/api/v1/users/client/stripe_webhook/
```

## Stripe + Signup Flow Notes (Current Behavior)

### Public / Admin-Branded Client Signup

- Free macro plan:
  - no Stripe checkout
  - creates pending signup directly (dev flow)

- Paid plans (weekly/monthly/premium):
  - require Stripe checkout
  - discount code validation happens in app backend
  - successful Stripe completion creates pending signup (via webhook)
  - registration link is printed to backend terminal (dev email simulation)

### First-Transaction Discount Behavior

Current intended behavior:
- Discount codes apply to the **first transaction only**
- Recurring price stays at the normal weekly/monthly plan amount
- Stripe one-time coupon is applied for the initial charge when app discount code is used

## Discount Codes (Development)

There are currently separate models for:
- Client/end-user discount codes (`client_area`)
- Admin purchase discount codes (`admin_area`)

Django admin can be used to create/manage codes for either group.

Reset behavior:
- `reset_all` now clears discount code records (client + admin) in addition to other local test data

## Database Reset Commands

Reset app test data (keeps DB, clears many records):
```bash
cd backend
source venv/bin/activate
python manage.py reset_all
```

Full local database recreation:
```bash
python manage.py full_reset_db
```

If code changes add models/migrations, run this before reset:
```bash
python manage.py migrate
```

## Testing

Backend:
```bash
cd backend
source venv/bin/activate
python manage.py test
```

Frontend build check:
```bash
cd frontend
npm run build
```

## In Progress / Next Major Work

- Premium client coaching dashboard (gated by plan/entitlements)
- Admin discount code application in admin Stripe purchase flows
- Discount redemption tracking / audit trail
- Production-grade AI recipe suggestion quality + controls
- Coaching features (chat, progress photos, stats journal, check-ins)

