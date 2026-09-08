#!/usr/bin/env bash
# HomeLedger - Fast Start Development Servers for Linux and macOS
set -e

if [ ! -d "backend/venv" ] || [ ! -d "frontend/node_modules" ]; then
    echo -e "\033[1;33m[HomeLedger] Dependencies not detected. Running setup first...\033[0m"
    ./setup.sh
fi

echo -e "\n\033[1;32m=== [HomeLedger] Starting Development Servers ===\033[0m"
echo -e "\033[1;36mBackend API:    http://localhost:8000\033[0m"
echo -e "\033[1;36mAPI Swagger:    http://localhost:8000/docs\033[0m"
echo -e "\033[1;36mFrontend App:   http://localhost:5173\033[0m"
echo -e "\n\033[1;33mPress Ctrl+C to stop both servers.\033[0m\n"

# Trap SIGINT and SIGTERM to kill child processes
cleanup() {
    echo -e "\n\033[1;33m[HomeLedger] Shutting down servers...\033[0m"
    kill 0
    exit 0
}
trap cleanup SIGINT SIGTERM

# Run Backend
cd backend
./venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
cd ..

sleep 1

# Run Frontend
cd frontend
npm run dev &
cd ..

# Wait for background processes
wait
