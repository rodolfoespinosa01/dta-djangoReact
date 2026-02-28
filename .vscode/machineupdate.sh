echo "🔄 Pulling latest from origin/main..."
git pull origin main

echo "🐍 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing backend Python dependencies..."
pip install -r backend/requirements.txt

echo "🧼 Running makemigrations..."
python backend/manage.py makemigrations --noinput

echo "🔧 Running migrate..."
python backend/manage.py migrate

echo "🧹 Clearing pending admin tokens..."
python backend/manage.py reset_all

echo "💻 Installing frontend dependencies..."
cd frontend
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
elif [ -s "/opt/homebrew/opt/nvm/nvm.sh" ]; then
  . "/opt/homebrew/opt/nvm/nvm.sh"
else
  echo "❌ nvm not found"
  exit 1
fi
nvm install
nvm use
npm install

echo "✅ All set! You can now:"
echo "➡️  Run backend:  source backend/venv/bin/activate && python backend/manage.py runserver"
echo "➡️  Run frontend: cd frontend && npm run dev"

cd ..
