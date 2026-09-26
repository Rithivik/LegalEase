#!/usr/bin/env bash
# Starts the FastAPI backend and the Streamlit frontend together (macOS / Linux / Git Bash).
cd "$(dirname "$0")"
[ -d venv ] && source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
uvicorn legalEaseAPI.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
trap "kill $BACKEND_PID 2>/dev/null" EXIT
sleep 3
streamlit run frontend/app.py
