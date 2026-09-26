"""
routes.py - API routes for LegalEase.

Endpoints
---------
POST /generate        -> generate a legal document with Gemini
POST /export/{fmt}    -> convert (edited) text into a txt / docx / pdf download
GET  /document-types  -> suggested document types for the UI
GET  /health          -> service status (model, mock mode)
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

import config
from ai_core.gemini_generator import GeminiDocumentGenerator, GenerationError
from ai_core.generator import (format_docx, format_pdf, format_txt, safe_filename,
                               sanitize_text)

logger = logging.getLogger("legalease.api")
router = APIRouter()


@lru_cache(maxsize=1)
def get_generator() -> GeminiDocumentGenerator:
    """Create the Gemini generator once and reuse it for every request."""
    return GeminiDocumentGenerator()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class DocumentRequest(BaseModel):
    document_type: str = Field(..., min_length=2, max_length=200,
                               examples=["Freelance Work Contract"])
    parties: str = Field(..., min_length=2, max_length=config.MAX_FIELD_LENGTH,
                         examples=["Jane Doe (Service Provider), TechNova Inc. (Client)"])
    terms: str = Field(..., min_length=2, max_length=config.MAX_FIELD_LENGTH,
                       examples=["Payment within 30 days of invoice; Confidentiality at all times"])
    dates: str = Field(..., min_length=2, max_length=200, examples=["April 15, 2025"])
    # Optional extras (not required by the original spec)
    jurisdiction: str = Field("", max_length=200, examples=["Tamil Nadu, India"])
    additional_instructions: str = Field("", max_length=config.MAX_FIELD_LENGTH)

    @field_validator("document_type", "parties", "terms", "dates")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("must not be empty")
        return v

    @field_validator("jurisdiction", "additional_instructions")
    @classmethod
    def strip_optional(cls, v: str) -> str:
        return v.strip()


class DocumentResponse(BaseModel):
    document: str
    document_type: str
    model: str
    mock: bool


class ExportRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)
    document_type: str = Field("Legal Document", max_length=200)
    terms: str = Field("", max_length=config.MAX_FIELD_LENGTH)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=DocumentResponse, tags=["Documents"])
async def generate_legal_document(request: DocumentRequest):
    """Generate a legal document from the user's inputs."""
    generator = get_generator()
    try:
        # Gemini SDK call is blocking -> run it in a worker thread
        text = await run_in_threadpool(
            generator.generate_document,
            request.document_type,
            request.parties,
            request.terms,
            request.dates,
            request.jurisdiction,
            request.additional_instructions,
        )
    except GenerationError as exc:
        logger.error("Generation failed: %s", exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # never leak a raw traceback to the client
        logger.exception("Unexpected generation error")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")

    return DocumentResponse(
        document=sanitize_text(text),
        document_type=request.document_type,
        model="mock" if generator.mock else generator.model_name,
        mock=generator.mock,
    )


_MEDIA = {
    "txt": "text/plain; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.post("/export/{fmt}", tags=["Documents"])
async def export_document(fmt: Literal["txt", "docx", "pdf"], request: ExportRequest):
    """Convert document text (e.g. after editing) into a downloadable file."""
    text = sanitize_text(request.text)
    try:
        if fmt == "txt":
            data = format_txt(text).encode("utf-8")
        elif fmt == "docx":
            data = await run_in_threadpool(format_docx, text, request.document_type, request.terms)
        else:
            data = await run_in_threadpool(format_pdf, text, request.document_type, request.terms)
    except Exception as exc:
        logger.exception("Export failed")
        raise HTTPException(status_code=500, detail=f"Could not create {fmt.upper()}: {exc}")

    filename = safe_filename(request.document_type, fmt)
    return Response(content=data, media_type=_MEDIA[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/document-types", tags=["Info"])
def document_types():
    return {"document_types": config.DOCUMENT_TYPES}


@router.get("/health", tags=["Info"])
def health():
    """Service status. Always answers quickly and never crashes, so the
    frontend can show the real problem instead of 'not reachable'."""
    info = {
        "status": "ok",
        "model": config.GEMINI_MODEL,
        "mock_mode": False,
        "api_key_configured": bool(config.GEMINI_API_KEY),
    }
    try:
        gen = get_generator()
        info["model"] = gen.model_name
        info["mock_mode"] = gen.mock
    except GenerationError as exc:
        info["status"] = "error"
        info["error"] = exc.message
    except Exception as exc:  # e.g. a broken install
        info["status"] = "error"
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info
