# CricketIQ Automated Environment Setup Script (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "           CricketIQ - Environment Setup                 " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python version
Write-Host "[1/7] Checking Python version..." -ForegroundColor Yellow
$PythonCmd = ""
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3.12"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} else {
    Write-Error "Python 3.12+ is required. Please install Python 3.12 and ensure it is on your PATH."
    exit 1
}

$PyVer = Invoke-Expression "$PythonCmd -c `"import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')`""
Write-Host "[+] Found Python $PyVer" -ForegroundColor Green

# 2. Check Node & npm
Write-Host "[2/7] Checking Node.js and npm..." -ForegroundColor Yellow
if (-not (Get-Command "node" -ErrorAction SilentlyContinue) -or -not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js (>=20.0.0) and npm are required. Please install Node.js."
    exit 1
}
$NodeVer = node -v
$NpmVer = npm -v
Write-Host "[+] Found Node.js $NodeVer and npm $NpmVer" -ForegroundColor Green

# 3. Setup Python Virtual Environment
Write-Host "[3/7] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path "$RootDir\.venv")) {
    Invoke-Expression "$PythonCmd -m venv .venv"
    Write-Host "[+] Created .venv" -ForegroundColor Green
} else {
    Write-Host "[+] Existing .venv found" -ForegroundColor Green
}

$VenvPython = "$RootDir\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = $PythonCmd
}

# 4. Install backend dependencies
Write-Host "[4/7] Installing pinned backend dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r backend/requirements.txt
& $VenvPython -m pip install -r backend/requirements-dev.txt
Write-Host "[+] Python dependencies installed." -ForegroundColor Green

# 5. Download AI Models with SHA256 Verification
Write-Host "[5/7] Downloading and verifying MediaPipe model assets..." -ForegroundColor Yellow
& $VenvPython scripts/download_models.py
Write-Host "[+] Model assets verified." -ForegroundColor Green

# 6. Initialize Environment and Database
Write-Host "[6/7] Initializing environment and database..." -ForegroundColor Yellow
if (-not (Test-Path "$RootDir\.env")) {
    Copy-Item "$RootDir\.env.example" "$RootDir\.env"
    Write-Host "[+] Copied .env.example -> .env" -ForegroundColor Green
}
& $VenvPython -c "from backend.app.repositories.session_repository import session_repo; session_repo._init_db(); print('Database ready at:', session_repo.db_path)"

# 7. Setup Frontend dependencies & build
Write-Host "[7/7] Setting up frontend dependencies and compiling assets..." -ForegroundColor Yellow
Set-Location "$RootDir\frontend"
npm install --no-audit --no-fund
npm run build
Set-Location $RootDir

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  CricketIQ setup completed successfully!                 " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "To start the development server:" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor Cyan
Write-Host "  OR" -ForegroundColor White
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/dev.ps1" -ForegroundColor Cyan
Write-Host ""
