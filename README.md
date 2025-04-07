# 🥗 DTA – Diet Generator Platform (Django + React)

**DTA** is a scalable diet plan generator designed to support both **B2C** (direct to consumer) and **B2B** (fitness influencers & coaches) models. Built using Django (backend) and React (frontend), this platform enables personalized meal plan delivery based on lifestyle goals and algorithmic precision.

---

## 🚀 Project Structure

```
dta-djangoReact/
├── backend/                # Django backend (Custom User, API, Logic)
│   ├── manage.py
│   └── backend/            # Django settings, URLs, celery, wsgi
├── frontend/               # React frontend (UI/UX for users)
├── backend/venv/           # Python virtual environment (ignored)
├── startapp.sh             # Script to start all services
├── machineupdate.sh        # Script to update project on new machine
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 🌐 User Types & Flows

### 👤 End Users (B2C)
- Sign up via Google, Facebook, or Email
- Choose a plan (Free Trial or Paid)
- Complete questionnaire
- Receive AI-generated meal plans
- View/Download weekly nutrition plans

### 👩‍💼 Admins (B2B)
- Sign up for a 2-week trial (max 10 clients)
- Upgrade to Monthly or Annual subscription
- Manage their own clients & dashboards
- Invite clients via unique referral link
- White-label options (branding, logos)

### 👑 SuperAdmin (You)
- View/manage all Admins and End Users
- Adjust subscriptions and access
- Configure global system settings

---

## 🛠 Tech Stack

| Layer     | Tech                           |
|-----------|----------------------------------|
| Backend   | Django + DRF                     |
| Frontend  | React + Axios                    |
| Database  | PostgreSQL                       |
| Auth      | Custom User Model                |
| Payments  | Stripe, PayPal, Apple Pay (planned) |
| Queueing  | Celery + Redis                   |
| Deploy    | (Planned: Docker, Heroku, AWS)   |

---

## 🧱 Key Features (in progress)

- [x] Custom User Model with roles (SuperAdmin, Admin, EndUser)
- [x] Admin trial logic (2 weeks)
- [x] Stripe + webhook integration
- [x] Task queues with Celery & Redis
- [x] Protected dashboard routing (React)
- [ ] Questionnaire & AI meal engine
- [ ] PDF export of meal plans
- [ ] White-label dashboards
- [ ] End user invite + onboarding

---

## 📦 Setup Instructions

### 🔧 Prerequisites
Install these first:
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

### 🔐 Environment Variables
Make sure to add your Stripe keys, database URL, etc. in your `.env` files in:
- `backend/.env`
- `frontend/.env`

Example:
```env
# backend/.env
STRIPE_SECRET_KEY=sk_test_xxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxx
```

---

## 🧠 B2B License Model
Admins (fitness influencers, coaches) can:
- Start with a 2-week trial
- Upgrade to monthly or annual
- White-label dashboard (coming soon)

---

## 👑 SuperAdmin Privileges
- View/manage all users
- Access all admin subscriptions
- Oversee platform revenue
- Trigger admin bans, plan upgrades

---

## 📬 Questions / Feedback?
Feel free to open an issue or submit a PR if you're contributing.