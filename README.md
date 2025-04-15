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

