#!/bin/zsh
set -e

# Automate creating an admin for local dev
# Usage: ./auto_create_admin.sh

echo "🔧 Creating admin test@admin.com on monthly plan (dev)"
cd backend
if [ ! -f venv/bin/activate ]; then
  echo "⚠️ virtualenv not found at backend/venv. Activate your env manually and run the python command:" 
  echo "python manage.py simulate_create_admin test@admin.com --password test1234 --plan_name adminMonthly --initialize_parameters --admin_slug rodolfo"
  exit 1
fi

source venv/bin/activate
python manage.py simulate_create_admin test@admin.com --password test1234 --plan_name adminMonthly --initialize_parameters --admin_slug rodolfo

echo "\n✅ Done. Admin created (email: test@admin.com, slug: rodolfo)."