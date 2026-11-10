#!/usr/bin/env bash
# CricketIQ Automated Environment Setup Script (POSIX / Bash)
# Usage: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo -e "\033[36m==========================================================\033[0m"
echo -e "\033[36m           CricketIQ - Environment Setup                 \033[0m"
echo -e "\033[36m==========================================================\033[0m"

# 1. Check Python version
echo -e "\033[33m[1/7] Checking Python version...\033[0m"
if command -v python3.12 &>/dev/null; then
    PY_CMD="python3.12"
elif command -v python3 &>/dev/null; then
    PY_CMD="python3"
else
    PY_CMD="python"
fi

PY_VER=$($PY_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "\033[32m[+] Found Python $PY_VER\033[0m"

# 2. Check Node & npm
echo -e "\033[33m[2/7] Checking Node.js and npm...\033[0m"
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    echo "Error: Node.js (>=20.0.0) and npm are required."
    exit 1
fi
echo -e "\033[32m[+] Found Node $(node -v) and npm $(npm -v)\033[0m"

# 3. Virtualenv
echo -e "\033[33m[3/7] Setting up Python virtual environment (.venv)...\033[0m"
if [ ! -d "$ROOT_DIR/.venv" ]; then
    $PY_CMD -m venv "$ROOT_DIR/.venv"
    echo -e "\033[32m[+] Created .venv\033[0m"
else
    echo -e "\033[32m[+] Existing .venv found\033[0m"
fi

VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$PY_CMD"
fi

# 4. Dependencies
echo -e "\033[33m[4/7] Installing pinned backend dependencies...\033[0m"
$VENV_PYTHON -m pip install --upgrade pip
$VENV_PYTHON -m pip install -r backend/requirements.txt
$VENV_PYTHON -m pip install -r backend/requirements-dev.txt
echo -e "\033[32m[+] Python dependencies installed.\033[0m"

# 5. Model Assets
echo -e "\033[33m[5/7] Downloading and verifying MediaPipe model assets...\033[0m"
$VENV_PYTHON scripts/download_models.py
echo -e "\033[32m[+] Model assets verified.\033[0m"

# 6. Environment & Database
echo -e "\033[33m[6/7] Initializing environment and database...\033[0m"
if [ ! -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo -e "\033[32m[+] Copied .env.example -> .env\033[0m"
fi
$VENV_PYTHON -c "from backend.app.repositories.session_repository import session_repo; session_repo._init_db(); print('Database ready at:', session_repo.db_path)"

# 7. Frontend
echo -e "\033[33m[7/7] Setting up frontend dependencies and compiling assets...\033[0m"
(cd frontend && npm install --no-audit --no-fund && npm run build)

echo -e "\n\033[32m==========================================================\033[0m"
echo -e "\033[32m  CricketIQ setup completed successfully!                 \033[0m"
echo -e "\033[32m==========================================================\033[0m"
echo -e "To start the development server:"
echo -e "  \033[36mnpm run dev\033[0m"
echo -e "  OR"
echo -e "  \033[36m./scripts/dev.sh\033[0m\n"
