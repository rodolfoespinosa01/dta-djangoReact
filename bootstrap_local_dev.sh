#!/bin/bash

echo "🔄 Pulling latest from origin/main..."
git pull origin main

echo "🐍 Activating virtual environment..."
source backend/venv/bin/activate

echo "📦 Installing backend Python dependencies..."
pip install -r backend/requirements.txt

echo "🧼 Running makemigrations..."
python backend/manage.py makemigrations --noinput

echo "🔧 Running migrate..."
python backend/manage.py migrate

echo "🧹 Clearing pending admin tokens..."
python backend/manage.py reset_admins

echo "💻 Installing frontend dependencies..."
cd frontend
npm install

echo "✅ All set! You can now:"
echo "➡️  Run backend:  source backend/venv/bin/activate && python backend/manage.py runserver"
echo "➡️  Run frontend: cd frontend && npm run dev"

cd ..
