#!/usr/bin/env bash
# HomeLedger - Fast Setup Script for Linux and macOS
set -e

echo -e "\n\033[1;32m=== [HomeLedger] Fast Configuration & Setup ===\033[0m"

# 1. Check Prerequisites
echo -e "\n\033[1;36m[1/5] Checking environment prerequisites...\033[0m"
command -v python3 >/dev/null 2>&1 || { echo >&2 "Python 3 is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo >&2 "Node.js / npm is required but not installed."; exit 1; }

# 2. Python Virtual Environment
echo -e "\n\033[1;36m[2/5] Initializing Python virtual environment in backend/venv...\033[0m"
if [ ! -d "backend/venv" ]; then
    python3 -m venv backend/venv
fi

# 3. Backend Dependencies
echo -e "\n\033[1;36m[3/5] Installing backend dependencies via pip...\033[0m"
./backend/venv/bin/pip install --upgrade pip --quiet
./backend/venv/bin/pip install -r backend/requirements.txt --quiet

# 4. Database Migrations
echo -e "\n\033[1;36m[4/5] Applying database migrations with Alembic...\033[0m"
cd backend
./venv/bin/alembic upgrade head
cd ..

# 5. Frontend Dependencies
echo -e "\n\033[1;36m[5/5] Installing frontend dependencies via npm...\033[0m"
cd frontend
npm install --silent
cd ..

echo -e "\n\033[1;32m=== [HomeLedger] Setup Completed Successfully! ===\033[0m"
echo -e "\033[1;33mTo launch the development stack, run: ./start-dev.sh\033[0m\n"
