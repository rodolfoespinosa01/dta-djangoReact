# 🥗 DTA – Diet Generator Platform (Django + React)

**DTA** is a scalable AI-powered diet plan generator designed for both **B2C** (individual clients) and **B2B** (fitness influencers & coaches). Built with Django + React, the platform delivers personalized meal plans based on lifestyle goals and algorithmic precision.

---

## 🚀 Project Structure

---

## 🌐 User Types & Flows

### 👤 End Users (Clients)
- Coming soon: Questionnaire + Meal Plan UI

### 👩‍💼 Admins (Fitness Coaches)
- Sign up via Stripe checkout (Free Trial, Monthly, or Annual)
- Receive email link to complete registration
- Get 14-day trial (1-time only)
- Can cancel trial auto-upgrade from `/adminsettings`
- After 14 days: upgraded to paid plan via Celery
- Access dashboard, client tools, settings

### 👑 SuperAdmin (Platform Owner)
- Full visibility into admin accounts and billing
- View revenue, control admin statuses
- Access protected dashboard `/superadmindashboard`

---

## 🛠 Tech Stack

| Layer     | Tech                     |
|-----------|--------------------------|
| Backend   | Django, Django REST      |
| Frontend  | React + Axios            |
| Database  | PostgreSQL               |
| Auth      | Custom User Model (JWT)  |
| Payments  | Stripe (webhooks)        |
| Queueing  | Celery + Redis           |
| Testing   | Django `unittest`, Cypress (planned) |

---

## 🧱 Key Features

- ✅ Admin trial flow w/ Stripe checkout
- ✅ Celery-powered auto-upgrade to paid
- ✅ Cancel auto-renew during trial
- ✅ SuperAdmin dashboard w/ revenue
- ✅ JWT auth, protected routes, role logic
- ✅ Test structure (admin/superadmin/unit)
- 🧠 AI meal engine (upcoming)
- 🖼️ White-label client dashboards (upcoming)

---

## 📦 Setup Instructions

### 🔧 Prerequisites
```bash
brew install redis
brew install postgresql
brew services start redis
brew services start postgresql

```

Install Python 3.11.9 (via pyenv or system Python):
```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

---

### 🐍 Backend Setup
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

Optional: Reset environment for clean test
```bash
python manage.py reset_all
```

---

### ⚛️ Frontend Setup
```bash
cd frontend
npm install
npm start
```

---

### 🔁 Background Services

**Start Celery Worker (for async tasks like auto-upgrades):**
```bash
cd backend
source venv/bin/activate
celery -A backend worker --loglevel=info
```

**Start Stripe Webhook Listener:**
```bash
stripe listen --forward-to localhost:8000/api/stripe-webhook/
```

---

### 🚀 Launch Full App via Script
```bash
./startapp.sh
```

This will:
- Start backend (Django)
- Start frontend (React)
- Start Celery
- Start Stripe webhook listener
Each in its own Terminal window.

---

### Backend Testing
Run all tests (admin/superadmin)
- `python manage.py test`

Test Includes:
- Auth and login access
- SuperAdmin protection
- Trial-to-paid logic
- Token refresh logic
- Cancel trial logic
- Dashboard protection


### Backend Testing
STRIPE_SECRET_KEY=sk_test_XXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXX


---

## 🧠 B2B License Model
🧠 License Logic

Admins can:

Start 1 trial
Cancel auto-upgrade
Upgrade via Stripe
Manage dashboard
Once trial is canceled or expired:

They see inactive status
Must upgrade to resume access

---

## 👑 SuperAdmin Privileges
- View/manage all users
- Access all admin subscriptions
- Oversee platform revenue
- Trigger admin bans, plan upgrades

---

## 📬 Questions / Feedback?
Feel free to open an issue or submit a PR if you're contributing.




## 🚧 Pending Features and Refactor Checklist

### ✅ Account History Tracking
- [ ] Create `AdminAccountHistory` model to track:
  - Trial start
  - Plan upgrade/downgrade
  - Cancellation
  - Reactivation
  - Timestamps and status changes
- [ ] Log history entries in:
  - `register_admin()`
  - `auto_upgrade_admin_trial()`
  - Cancel views (monthly/annual)
  - Reactivation & transitions

---

### 🔐 Protected Plan Purchase Flow for Existing Admins
- [ ] Create a new **authenticated page** for logged-in admins to:
  - Upgrade from monthly to annual
  - Downgrade from annual to monthly
  - Reactivate after becoming inactive
- [ ] Restrict **Free Trial** to first-time users only
- [ ] Validate all plan transitions with Stripe

---

### ⚠️ Prevent Duplicate Stripe Sessions
- [ ] If `PendingAdminSignup` already exists:
  - Show message: "You have a pending registration. Please check your email."
- [ ] If user already exists:
  - Require login before purchasing new plans

---

### 🔁 Scheduled Plan Switching Logic
- [ ] Allow:
  - Monthly → Annual (scheduled at end of billing cycle)
  - Annual → Monthly (downgrade after annual term ends)
- [ ] Add `pending_plan_change` field to `AdminProfile`
- [ ] Trigger updates via webhook or scheduled task

---

## 🧹 Codebase Cleanup & Refactor

### 🗂 Backend File Structure
- [ ] Split `views.py` into:
  - `views/auth.py`
  - `views/billing.py`
  - `views/dashboard.py`
- [ ] Create logical folders (e.g. `adminplans/stripe/`)
- [ ] Rename generic files (e.g. `tasks.py` → `billing_tasks.py`)

---

### ⚙️ Django Admin Panel Enhancements
- [ ] Improve `AdminProfile` and `PendingAdminSignup` layouts
- [ ] Add filters for:
  - Active/inactive status
  - Subscription type
  - Cancelled accounts
- [ ] Enable email & Stripe ID search

---

### 🧪 Developer & Testing Tools
- [ ] Add `AdminAccountHistory` reset tool in `reset_all.py`
- [ ] Create test accounts:
  - `trial_test@`, `monthly_test@`, `annual_test@`
- [ ] Add log printouts:
  - "⏳ Scheduled downgrade"
  - "✅ Billing update recorded"

---




✅ DTA MASTER BACKEND TEST LIST – VERIFIED FEATURES ONLY

🔐 Auth & Access Control
✅ Admin login with correct credentials
✅ Admin login with invalid credentials
✅ Admin cannot access dashboard if not logged in
✅ Admin session persists after page refresh (via token)
✅ Token auto-refresh logic (Admin)
✅ SuperAdmin login and access to /superadmin/dashboard
✅ Token auto-refresh logic (SuperAdmin)
✅ Admin cannot access SuperAdmin routes

👨‍💼 Admin Registration & Free Trial
✅ Stripe webhook creates PendingAdminSignup
✅ Token-based admin registration succeeds
✅ Free trial user created with:

✅ subscription_status = admin_trial
✅ AdminProfile auto-created
✅ trial_start_date is set
✅ subscription_started_at is null
✅ admin_stripe_customer_id is stored
💸 Stripe Billing & Plan Management
✅ Paid plan registration (monthly/annual) stores:

✅ subscription_status = admin_monthly/admin_annual
✅ admin_stripe_subscription_id
✅ subscription_started_at and next_billing_date
✅ Admin cancels subscription during trial or paid plan
✅ auto_renew_cancelled=True is respected

📬 Token & Signup Flow
✅ Token is generated and stored on webhook
✅ Token becomes invalid after one use
✅ Invalid or reused token errors gracefully
✅ Registration pulls email from token record

📊 SuperAdmin Dashboard
✅ Displays trial, monthly, annual, and inactive admins
✅ Shows amount paid per admin and next billing date
✅ Highlights inactive admins in red

🔑 Admin Password Reset (Confirmed in Flow)
✅ Forgot password request saves token
✅ Reset URL simulates email print
✅ Password can be changed
✅ Old password fails, new one works

🧹 Dev Scripts / Environment Health
✅ reset_all clears users and resets DB
✅ machineupdate.sh pulls latest, installs deps, runs migrations
✅ startapp.sh launches backend, frontend, webhook, celery (if used)
✅ .env variables load (Stripe, DB)
✅ PostgreSQL + Redis connection verified
✅ Stripe keys work (test mode)




👨‍💼 Admin Registration & Free Trial
✅ test_admin_token_cannot_be_reused.py
✅ test_admin_invalid_or_expired_token.py

💸 Stripe & Billing
✅ test_admin_paid_plan_registration_monthly.py
✅ test_admin_paid_plan_registration_annual.py

🔐 Password Reset Flow
✅ test_admin_forgot_password_token_created.py
✅ test_admin_reset_password_success.py
✅ test_admin_old_password_fails_new_pass_works.py

📊 SuperAdmin Dashboard
✅ test_superadmin_dashboard_admin_grouping.py
✅ test_superadmin_dashboard_amounts_render.py



IMMEDIATE DEVELOPMENT - CANCEL LOGIC FOR ALL TYPES OF PLAN, CONFIRM IT WORKS AND WE ARE CAPTURING DATA