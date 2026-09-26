"""Tests for ai_core/gemini_generator.py (no network: mock mode and a fake client)."""
from types import SimpleNamespace

import pytest

from ai_core.gemini_generator import GeminiDocumentGenerator, GenerationError


def test_prompt_contains_all_inputs():
    prompt = GeminiDocumentGenerator.build_prompt(
        "NDA", "Alice (Discloser), Bob (Recipient)", "Keep secrets; 2 years", "May 1, 2025",
        jurisdiction="India", additional_instructions="Add non-solicit")
    for piece in ("NDA", "Alice (Discloser)", "- Keep secrets", "- 2 years", "May 1, 2025",
                  "India", "Add non-solicit"):
        assert piece in prompt


def test_mock_mode_when_no_key():
    gen = GeminiDocumentGenerator(api_key="")
    assert gen.mock is True
    doc = gen.generate_document("Lease Agreement", "Alice Smith (Tenant), XYZ Realty (Landlord)",
                                "Rent due on 5th; Deposit refundable", "June 1, 2025")
    assert doc.startswith("## Lease Agreement")
    assert "Alice Smith (Tenant)" in doc and "Rent due on 5th" in doc and "June 1, 2025" in doc


def test_clean_output_strips_code_fences():
    assert GeminiDocumentGenerator._clean_output("```markdown\n## Hi\n```") == "## Hi"


def test_real_path_with_fake_client():
    pytest.importorskip("google.genai")
    gen = GeminiDocumentGenerator(api_key="", mock=True)
    gen.mock = False
    gen.client = SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **kw: SimpleNamespace(text="```\n## Test Doc\nBody\n```")))
    assert gen.generate_document("Test", "A, B", "x", "today") == "## Test Doc\nBody"


def test_empty_response_raises():
    pytest.importorskip("google.genai")
    gen = GeminiDocumentGenerator(api_key="", mock=True)
    gen.mock = False
    gen.client = SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **kw: SimpleNamespace(text=None)))
    with pytest.raises(GenerationError) as exc:
        gen.generate_document("Test", "A, B", "x", "today")
    assert exc.value.status_code == 502
