#!/bin/zsh

set -e  # Exit on any error

echo "� Resetting database data...\n"

# call the existing django command to clear tables
cd backend
source venv/bin/activate
python manage.py reset_all

echo "\n✅ Database reset complete!\n"