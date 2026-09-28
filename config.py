"""
config.py - Central configuration for LegalEase.

All settings are read from the .env file in the project root (or from real
environment variables, which take priority). Every module imports its
settings from here so there is exactly one place to change them.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "Image"

# Load .env from the project root no matter where the app is started from
load_dotenv(BASE_DIR / ".env")

# Logo used inside DOCX / PDF files (dark logo on white paper)
LOGO_PATH = str(IMAGE_DIR / "Logo.png")
# Logo shown in the Streamlit web UI (light logo for the dark theme)
WEB_LOGO_PATH = str(IMAGE_DIR / "inverseLogo.png")

# ---------------------------------------------------------------------------
# Gemini / AI settings
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# The project document selected "gemini-1.5-pro". Google has since retired the
# 1.5 models, so the default is the "gemini-flash-latest" alias, which always
# points to Google's current Flash model. Change it in .env at any time,
# e.g. GEMINI_MODEL=gemini-2.5-pro
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()

# Models tried in order if the main model is unavailable for your key
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest,gemini-flash-latest"
    ).split(",")
    if m.strip()
]

GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "8192"))

# MOCK_MODE=true returns a built-in sample document instead of calling Gemini.
# Useful for testing the whole app without an API key or internet.
# If no API key is set, mock mode switches on automatically.
MOCK_MODE = os.getenv("MOCK_MODE", "false").strip().lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Backend / frontend connection
# ---------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
# URL the Streamlit frontend uses to reach the FastAPI backend
BACKEND_URL = os.getenv("BACKEND_URL", f"http://{API_HOST}:{API_PORT}").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))

# Comma-separated list of origins allowed to call the API (CORS)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# Branding (used in DOCX / PDF footers)
# ---------------------------------------------------------------------------
COMPANY_NAME = os.getenv("COMPANY_NAME", "LegalEase Inc.")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "contact@legalease.com")
FOOTER_TEXT = f"{COMPANY_NAME} | {COMPANY_EMAIL} | All Rights Reserved."
DISCLAIMER = (
    "This document was generated with AI assistance and is provided for "
    "informational purposes only. It is not legal advice. Please have it "
    "reviewed by a qualified lawyer before signing."
)

# Supported document types shown in the UI (users may also type their own)
DOCUMENT_TYPES = [
    "Non-Disclosure Agreement (NDA)",
    "Employment Contract",
    "Employment Offer Letter",
    "Freelance Work Contract",
    "Residential Lease Agreement",
    "Commercial Lease Agreement",
    "Service Agreement",
    "Partnership Agreement",
    "Consulting Agreement",
    "Sales Agreement",
    "Memorandum of Understanding (MoU)",
    "Power of Attorney",
]

# Input limits (protect the API from very large payloads)
MAX_FIELD_LENGTH = 5000
