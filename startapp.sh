#!/bin/bash

echo "🚀 Launching DTA Dev Environment..."

# 🐍 Django Backend
osascript -e 'tell app "Terminal"
    do script "cd ~/Desktop/dta-djangoReact && source backend/venv/bin/activate && python backend/manage.py runserver"
end tell'

# ⚛️ React Frontend
osascript -e 'tell app "Terminal"
    do script "cd ~/Desktop/dta-djangoReact/frontend && npm start"
end tell'

# 🐇 Celery Worker
osascript -e 'tell app "Terminal"
    do script "cd ~/Desktop/dta-djangoReact/backend && source venv/bin/activate && celery -A backend worker --loglevel=info"
end tell'



# 💳 Stripe Webhook
osascript -e 'tell app "Terminal"
    do script "cd ~/Desktop/dta-djangoReact && stripe listen --forward-to localhost:8000/api/stripe-webhook/"
end tell'

echo "✅ All services launching in separate terminals!"
