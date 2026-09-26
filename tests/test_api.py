"""End-to-end tests of the FastAPI backend (mock mode, no API key needed)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from legalEaseAPI.main import app  # noqa: E402

client = TestClient(app)

PAYLOAD = {
    "document_type": "Freelance Work Contract",
    "parties": "Jane Doe (Service Provider), TechNova Inc. (Client)",
    "terms": "Work delivered by May 15, 2025; Payment within 7 days of invoice",
    "dates": "April 15, 2025",
}


def test_home():
    r = client.get("/")
    assert r.status_code == 200
    assert "Welcome to LegalEase" in r.json()["message"]


def test_health_reports_mock_mode():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["mock_mode"] is True


def test_document_types():
    assert "Employment Contract" in client.get("/document-types").json()["document_types"]


def test_generate_document():
    r = client.post("/generate", json=PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["mock"] is True
    assert "Freelance Work Contract" in body["document"]
    assert "Jane Doe" in body["document"] and "Payment within 7 days" in body["document"]


@pytest.mark.parametrize("missing", ["document_type", "parties", "terms", "dates"])
def test_generate_rejects_missing_fields(missing):
    data = {k: v for k, v in PAYLOAD.items() if k != missing}
    assert client.post("/generate", json=data).status_code == 422


def test_generate_rejects_blank_fields():
    assert client.post("/generate", json={**PAYLOAD, "parties": "   "}).status_code == 422


@pytest.mark.parametrize("fmt,magic", [("txt", b"FREELANCE"), ("docx", b"PK"), ("pdf", b"%PDF")])
def test_export(fmt, magic):
    doc = client.post("/generate", json=PAYLOAD).json()["document"]
    r = client.post(f"/export/{fmt}", json={"text": doc, "document_type": PAYLOAD["document_type"],
                                            "terms": PAYLOAD["terms"]})
    assert r.status_code == 200
    assert r.content.startswith(magic)
    assert "freelance_work_contract" in r.headers["content-disposition"]


def test_export_unknown_format():
    assert client.post("/export/rtf", json={"text": "x"}).status_code == 422
