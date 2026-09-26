"""Shared test setup: always run tests in MOCK mode (no real Gemini calls, no API key needed)."""
import os
import sys
from pathlib import Path

os.environ["MOCK_MODE"] = "true"
os.environ["GEMINI_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
