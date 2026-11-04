@echo off
echo ========================================================
echo Starting CricketIQ FastAPI Backend on http://127.0.0.1:8000
echo ========================================================
set PYTHONPATH=.
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend
pause
