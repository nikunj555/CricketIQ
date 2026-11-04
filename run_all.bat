@echo off
echo ========================================================
echo Launching CricketIQ Full Stack Application
echo ========================================================
start "CricketIQ Backend" cmd /k "run_backend.bat"
timeout /t 3 /nobreak >nul
start "CricketIQ Frontend" cmd /k "run_frontend.bat"
echo Services launched! Open http://localhost:5173 in your browser.
pause




