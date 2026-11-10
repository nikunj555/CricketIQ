# CricketIQ Local Development Startup Script (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/dev.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         CricketIQ - Starting Development Stack          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Resolve Python executable
$PythonExe = ""
if (Test-Path "$RootDir\.venv\Scripts\python.exe") {
    $PythonExe = "$RootDir\.venv\Scripts\python.exe"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $PythonExe = "py -3.12"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} else {
    Write-Error "Python 3.12 not found. Please run scripts/setup.ps1 first."
    exit 1
}

Write-Host "[+] Using Python: $PythonExe" -ForegroundColor Green

# 2. Check model assets
$PoseModel = "$RootDir\backend\app\models\assets\pose_landmarker_full.task"
if (-not (Test-Path $PoseModel)) {
    Write-Host "[*] Downloading required AI models..." -ForegroundColor Yellow
    Invoke-Expression "$PythonExe scripts/download_models.py"
}

# 3. Start Backend in separate process
Write-Host "[*] Launching CricketIQ FastAPI Backend (Port 8000)..." -ForegroundColor Yellow
$BackendJob = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-Command", "Set-Location '$RootDir'; $PythonExe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload" -PassThru

# 4. Start Frontend in separate process
Write-Host "[*] Launching CricketIQ React Frontend (Port 5173)..." -ForegroundColor Yellow
$FrontendJob = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-Command", "Set-Location '$RootDir\frontend'; npm run dev" -PassThru

# 5. Wait for Backend Health
Write-Host "[*] Waiting for backend to initialize..." -NoNewline
$MaxRetries = 60
$Ready = $false
for ($i = 0; $i -lt $MaxRetries; $i++) {
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline
    try {
        $Response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($Response.status -eq "healthy" -or $Response.status -eq "degraded") {
            $Ready = $true
            break
        }
    } catch {}
}
Write-Host ""

if ($Ready) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  CricketIQ is running and ready!                         " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  Frontend (Vite Dev) : http://localhost:5173/           " -ForegroundColor White
    Write-Host "  Backend API Docs    : http://127.0.0.1:8000/docs       " -ForegroundColor White
    Write-Host "  Health Endpoint     : http://127.0.0.1:8000/api/health " -ForegroundColor White
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop both servers.`n" -ForegroundColor Gray
} else {
    Write-Host "[!] Backend took longer than expected to start. Check terminal output." -ForegroundColor Yellow
}

# Register cleanup on exit
try {
    while ($true) {
        Start-Sleep -Seconds 2
        if ($BackendJob.HasExited -or $FrontendJob.HasExited) {
            break
        }
    }
} finally {
    Write-Host "`n[*] Stopping CricketIQ servers..." -ForegroundColor Cyan
    if ($BackendJob -and -not $BackendJob.HasExited) { Stop-Process -Id $BackendJob.Id -Force -ErrorAction SilentlyContinue }
    if ($FrontendJob -and -not $FrontendJob.HasExited) { Stop-Process -Id $FrontendJob.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "[+] All servers stopped cleanly." -ForegroundColor Green
}
