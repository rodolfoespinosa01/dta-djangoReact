#!/bin/zsh

set -e

echo "🚧 Setting up development environment...\n"

# Backend dependencies and migrations
cd backend
source venv/bin/activate

echo "📦 Installing Python requirements..."
pip install -r requirements.txt

echo "🗄 Applying database migrations..."
python manage.py migrate

# Frontend dependencies
cd ../frontend

# ensure nvm is loaded
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
elif [ -s "/opt/homebrew/opt/nvm/nvm.sh" ]; then
    . "/opt/homebrew/opt/nvm/nvm.sh"
else
    echo "⚠️ nvm not found, skipping npm steps"
    exit 0
fi

nvm install && nvm use

echo "📦 Installing npm packages..."
npm install --legacy-peer-deps


echo "\n✅ Setup complete!"