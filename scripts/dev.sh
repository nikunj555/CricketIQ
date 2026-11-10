#!/usr/bin/env bash
# CricketIQ Local Development Startup Script (POSIX / Bash)
# Usage: ./scripts/dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo -e "\033[36m==========================================================\033[0m"
echo -e "\033[36m         CricketIQ - Starting Development Stack          \033[0m"
echo -e "\033[36m==========================================================\033[0m"

# 1. Resolve Python
if [ -d "$ROOT_DIR/.venv" ]; then
    PYTHON_EXE="$ROOT_DIR/.venv/bin/python"
elif command -v python3.12 &>/dev/null; then
    PYTHON_EXE="python3.12"
elif command -v python3 &>/dev/null; then
    PYTHON_EXE="python3"
else
    PYTHON_EXE="python"
fi

echo -e "\033[32m[+] Using Python: $PYTHON_EXE\033[0m"

# 2. Check model assets
POSE_MODEL="$ROOT_DIR/backend/app/models/assets/pose_landmarker_full.task"
if [ ! -f "$POSE_MODEL" ]; then
    echo -e "\033[33m[*] Downloading required AI models...\033[0m"
    $PYTHON_EXE scripts/download_models.py
fi

# Cleanup handler
cleanup() {
    echo -e "\n\033[36m[*] Stopping CricketIQ servers...\033[0m"
    if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
    if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
    echo -e "\033[32m[+] All servers stopped cleanly.\033[0m"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 3. Start Backend
echo -e "\033[33m[*] Launching CricketIQ FastAPI Backend (Port 8000)...\033[0m"
$PYTHON_EXE -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# 4. Start Frontend
echo -e "\033[33m[*] Launching CricketIQ React Frontend (Port 5173)...\033[0m"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

# 5. Wait for Backend Health
echo -n "[*] Waiting for backend to initialize..."
for i in {1..30}; do
    sleep 1
    echo -n "."
    if curl -s http://127.0.0.1:8000/api/health | grep -q "healthy"; then
        break
    fi
done
echo ""

echo -e "\n\033[32m==========================================================\033[0m"
echo -e "\033[32m  CricketIQ is running and ready!                         \033[0m"
echo -e "\033[32m==========================================================\033[0m"
echo -e "  Frontend (Vite Dev) : \033[37mhttp://localhost:5173/\033[0m"
echo -e "  Backend API Docs    : \033[37mhttp://127.0.0.1:8000/docs\033[0m"
echo -e "  Health Endpoint     : \033[37mhttp://127.0.0.1:8000/api/health\033[0m"
echo -e "\033[32m==========================================================\033[0m"
echo -e "Press Ctrl+C to stop both servers.\n"

wait
