@echo off
REM Starts the FastAPI backend (new window) and the Streamlit frontend (Windows).
cd /d "%~dp0"
call venv\Scripts\activate.bat
start "LegalEase Backend" cmd /k "venv\Scripts\activate.bat && uvicorn legalEaseAPI.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 4 /nobreak >nul
streamlit run frontend\app.py
