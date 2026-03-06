#!/bin/zsh

set -e  # Exit on any error

echo "Resetting database data and uploaded media..."

# call the django command to clear tables and MEDIA_ROOT
cd backend
source venv/bin/activate
python manage.py reset_all

echo "Database + media reset complete."
