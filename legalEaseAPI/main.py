"""
main.py - FastAPI application entry point for LegalEase.

Run from the project root:
    uvicorn legalEaseAPI.main:app --reload
Then open http://127.0.0.1:8000/docs for the interactive API docs.
"""

import logging
import sys
from pathlib import Path

# Make the project root importable (config, ai_core) however the app is started
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

import config  # noqa: E402
from legalEaseAPI.routes import get_generator, router  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Gemini client once at startup, so the first request is fast."""
    try:
        gen = get_generator()
        logging.getLogger("legalease").info(
            "LegalEase ready - model=%s, mock_mode=%s", gen.model_name, gen.mock)
    except Exception as exc:
        logging.getLogger("legalease").error("Gemini setup failed: %s", exc)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="LegalEase - AI Legal Document Generator",
    description="Generate, edit and export legal documents with Google Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/", tags=["Info"])
def home():
    return {"message": "Welcome to LegalEase AI Legal Document Generator API",
            "docs": "/docs"}


# Run FastAPI if executed directly:  python legalEaseAPI/main.py
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
