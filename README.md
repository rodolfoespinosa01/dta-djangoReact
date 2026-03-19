# DTA - Django + React (Development)

DTA is a Django + React nutrition platform for:
- B2C (direct clients)
- B2B (admin/coaches)
- B2B2C (admin-branded client signup flows)

This repository is actively in development. The local development workflow is stable enough for day-to-day feature work, but several product areas are still being hardened.

## Current Status

- Client, admin, and superadmin areas are all present in the repo.
- Stripe purchase and signup flows exist and are still being refined for both direct-client and admin-branded flows.
- The meal-plan generation pipeline is actively being ported from legacy WordPress logic. Step 1 is implemented, and the current full-day path runs a collapsed server-side Steps 1-10 flow for saved meal combos.
- Meal Combinations and Food Library have been refactored so users choose real food names while combo matching still runs against canonical internal categories.
- Food, combo, and combo-error seed data now comes from root-level CSVs in `table_defaults` and is restored automatically during setup and reset.
- AI recipe suggestions remain a development-only feature.

## Recent Progress (March 2026)

- Food library entries now separate macro family from combo category bridge:
  - `macro` = Protein / Carbs / Fats / -
  - `name` = real user-facing food
  - `category` = canonical meal-combo slot category
- Combo lookup now accepts real food selections and resolves them back to canonical combo categories before matching templates.
- Saved questionnaire food preferences and generated meal details preserve real food names for display.
- The generation pipeline now uses the user's selected real foods for macro density lookups when available, with category-token fallback for backward compatibility.
- A new root refresh command loads default data from `table_defaults` using these preferred filenames:
  - `MYSQL_food_lib.csv`
  - `c_1_new.csv`
  - `errorid_453030.csv`
- `setup_dev.sh` now installs dependencies, runs migrations, and refreshes the food library defaults.
- `reset_all` now rebuilds the core food/combo/error tables from the same root CSV defaults.
- The combo importer was hardened to tolerate malformed or split combo CSV headers exported from spreadsheets.
- Recent migrations added the FoodLibraryItem macro/category bridge and resolved an existing `admin_area` migration branch conflict.
- At the time of writing, the current default seed snapshot loads:
  - 86 food library rows
  - 28916 meal combo template rows
  - 40500 combo error lookup rows

## AI Feature Status (Important)

AI recipe suggestions are not a finalized production feature yet.

Current state:
- MVP endpoint and UI exists for recipe ideas after meal generation
- Mock mode works for development and testing
- Optional OpenAI API integration is supported if a backend API key is configured
- Output quality, pricing controls, and production hardening are still in progress

ChatGPT Plus does not provide API credits for backend integration. OpenAI API usage requires a separate API key and billing setup.

## Tech Stack

- Backend: Django + Django REST Framework
- Frontend: React (CRA)
- Database: PostgreSQL
- Auth: JWT
- Payments: Stripe
- Queueing: Celery + Redis
- Local dev defaults: Django runserver + CRA dev server over HTTP, with optional manual HTTPS if needed

## Local Setup (Recommended)

### Prerequisites (macOS)

Core:

```bash
brew install redis postgresql
brew services start redis
brew services start postgresql
```

Optional, only if you want manual local HTTPS:

```bash
brew install mkcert nss
mkcert -install
```

### Fast Path

Create the backend virtual environment once, then use the repo setup script:

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
cd ..
./setup_dev.sh
```

What `setup_dev.sh` does now:
- installs backend Python requirements
- runs Django migrations
- refreshes the food/combo/error defaults from `table_defaults`
- installs frontend dependencies with `nvm` and `npm install --legacy-peer-deps`

### Manual Setup

Backend:

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py refresh_food_library_from_root
python manage.py createsuperuser
```

Frontend:

```bash
cd frontend
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm install
nvm use
npm install --legacy-peer-deps
```

## Seed Data / Algorithm Tables

The canonical local seed source is the root `table_defaults` directory.

Current preferred filenames:
- `MYSQL_food_lib.csv`
- `c_1_new.csv`
- `errorid_453030.csv`

Refresh the defaults manually:

```bash
cd backend
source venv/bin/activate
python manage.py refresh_food_library_from_root
```

Useful options:

```bash
python manage.py refresh_food_library_from_root --skip-error-table
python manage.py refresh_food_library_from_root --tables-dir /absolute/path/to/custom_tables
```

Notes:
- `refresh_food_library_from_root` prefers `table_defaults` and falls back to `backend/algorithmtables` if needed
- `reset_all` now calls this command automatically
- the importer excludes placeholder and category-reference rows from user-facing food options
- `standard_table.csv` is present in `table_defaults` but is not part of the food/combo/error refresh command

## Meal Combo + Food Library Behavior

- `MealComboTemplate` slot values remain canonical internal categories such as `Ground Beef STANDARD`.
- `FoodLibraryItem` rows can map many real foods to one combo category.
- Public slot option endpoints now return real food names, not just category tokens.
- Combo matching resolves selected food names back to categories before lookup.
- Generated meal details show selected real foods when available.
- Backward compatibility remains in place for older saved values that still contain category tokens.

## VS Code Tasks (Current)

Available tasks include:
- `Start All Services`
- `Run Django Server (Stable)`
- `Run React App`
- `Run Redis Server`
- `Run Celery Worker`
- `Run Stripe Webhook`
- `Run Stripe Webhook (Admin)`
- `Run Stripe Webhook (Client)`
- `Run Django Tests`
- `Setup Dev`
- `Reset All`
- `Full Reset DB`
- `Kill All Services`

Current task behavior:
- Django runs on `http://0.0.0.0:8000` using `manage.py runserver --noreload --nothreading`
- React runs on `http://0.0.0.0:3000` with `HTTPS=false`
- Redis task is idempotent on `:6379`
- Stripe webhook tasks forward to HTTP localhost endpoints with `--skip-verify`
- `Start All Services` launches Redis, Celery, Django, React, and the unified Stripe webhook listener in parallel

## Running the App

Use the VS Code tasks when possible.

### Manual

Backend:

```bash
cd backend
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000 --noreload --nothreading
```

Frontend:

```bash
cd frontend
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm use
HOST=0.0.0.0 HTTPS=false PORT=3000 npm start
```

Celery worker:

```bash
cd backend
source venv/bin/activate
celery -A core worker -l info
```

Unified Stripe webhook listener:

```bash
stripe listen --skip-verify --forward-to http://localhost:8000/api/v1/users/stripe_webhook/
```

Optional split listeners:

```bash
stripe listen --skip-verify --forward-to http://localhost:8000/api/v1/users/admin/stripe_webhook/
stripe listen --skip-verify --forward-to http://localhost:8000/api/v1/users/client/stripe_webhook/
```

## Optional Local HTTPS

Current VS Code tasks default to HTTP. If you want trusted local certs for manual runs:

```bash
mkdir -p .certs
mkcert -key-file .certs/localhost-key.pem -cert-file .certs/localhost.pem localhost 127.0.0.1 ::1 lvh.me "*.lvh.me"
```

Example Django manual HTTPS run:

```bash
cd backend
source venv/bin/activate
uvicorn core.asgi:application --host 0.0.0.0 --port 8000 --ssl-keyfile ../.certs/localhost-key.pem --ssl-certfile ../.certs/localhost.pem
```

## Stripe + Signup Flow Notes (Current Behavior)

### Public / Admin-Branded Client Signup

- Free macro plan:
  - no Stripe checkout
  - creates pending signup directly in the development flow

- Paid plans (weekly / monthly / premium):
  - require Stripe checkout
  - discount code validation happens in the app backend
  - successful Stripe completion creates pending signup via webhook
  - registration link is printed to the backend terminal in the dev email simulation flow

### First-Transaction Discount Behavior

- Discount codes apply to the first transaction only
- Recurring price stays at the normal weekly or monthly plan amount
- Stripe one-time coupon logic is used for the initial charge when an app discount code applies

## Discount Codes (Development)

- Separate discount code models currently exist in `client_area` and `admin_area`
- Django admin can be used to create and manage codes for either group
- `reset_all` clears local discount code records as part of the reset flow

## Database Reset Commands

Reset app test data while keeping the database:

```bash
cd backend
source venv/bin/activate
python manage.py reset_all
```

This now also reseeds the core food library, meal combo templates, and combo error lookup tables from `table_defaults`.

Full local database recreation:

```bash
cd backend
source venv/bin/activate
python manage.py full_reset_db
```

After pulling schema changes:

```bash
python manage.py migrate
```

## Testing and Validation

Backend tests:

```bash
cd backend
source venv/bin/activate
python manage.py test
```

Django system checks:

```bash
python manage.py check
```

Frontend build check:

```bash
cd frontend
npm run build
```

## In Progress / Next Major Work

- Further hardening and test coverage for the meal generation pipeline and category-bridge flow
- Premium client coaching dashboard and plan-gated coaching features
- Admin discount code application in admin Stripe purchase flows
- Discount redemption tracking and audit trail
- Production-grade AI recipe suggestion quality, controls, and pricing boundaries
- Coaching features such as chat, progress photos, stats journal, and check-ins
