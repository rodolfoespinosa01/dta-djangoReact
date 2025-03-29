# 🥗 DTA – Diet Generator Platform (Django + React)

**DTA** is a scalable AI-powered diet plan generator designed to support both **B2C** (direct to consumer) and **B2B** (fitness influencers & coaches) models. Built using Django (backend) and React (frontend), this platform enables personalized meal plan delivery based on lifestyle goals and algorithmic precision.

---

## 🚀 Project Structure

dta-djangoReact/ ├── backend/ # Django backend (Custom User, API, Logic) │ ├── manage.py │ └── backend/ # Django settings, URLs, wsgi ├── frontend/ # React frontend (UI/UX for users) ├── env/ # Python virtual environment (ignored) ├── .gitignore ├── README.md └── requirements.txt


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

| Layer     | Tech                 |
|-----------|----------------------|
| Backend   | Django + DRF         |
| Frontend  | React + Axios        |
| Database  | PostgreSQL           |
| Auth      | Custom User Model    |
| Payments  | Stripe, PayPal, Apple Pay (planned) |
| Queueing  | Celery + Redis (for plan processing, email) |
| Deploy    | (Planned: Docker, Heroku/Vercel/AWS) |

---

## 🧱 Key Features (in progress)

- [x] Custom User Model with roles (SuperAdmin, Admin, EndUser)
- [ ] Admin trial logic (2 weeks, 10 clients cap)
- [ ] Client onboarding via invite or referral
- [ ] Questionnaire auto-save flow
- [ ] Stripe integration with webhook support
- [ ] Meal Plan generation engine (AI + Algo)
- [ ] Role-based dashboards (B2C, B2B, SuperAdmin)

---

## 📦 Setup Instructions

### 🔧 Backend (Django)
```bash
cd backend
python -m venv env
source ../env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
🎨 Frontend (React)
cd frontend
npm install
npm start
🔐 Environment Variables

Create .env files for both frontend & backend as needed (e.g., for Stripe keys, DB, etc).

📌 Roadmap

 Finish Custom User Roles & API permissions
 Complete questionnaire + plan generator logic
 Full Stripe subscription integration
 Admin analytics dashboard
 PDF export of meal plans
 Deployment & Dockerization
 Build B2B onboarding and license management
 Explore white-label subdomains (e.g., fitcoach.dietapp.com)
🧠 License Model (B2B)

Admins (fitness influencers, coaches) can:

Start with a 2-week trial (max 10 clients)
Upgrade to monthly or annual plan
Use the app to manage their own clients
White-label their dashboard (coming soon)
👑 SuperAdmin Access

As the SuperAdmin, you:

Own the full platform logic and settings
Can view, create, or modify any user
Oversee all subscription plans and revenue
📬 Questions / Feedback?

Feel free to reach out or open an issue if you're collaborating on this project.