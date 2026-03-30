import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.docextract.app import app
from src.docextract.models import ExtractedInvoice

SAMPLE_INVOICE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "samples", "sample_invoice.txt"
)

MOCK_EXTRACTION = ExtractedInvoice(
    document_type="invoice",
    vendor_name="Acme Software Solutions",
    invoice_number="INV-2026-0042",
    invoice_date="2026-03-15",
    due_date="2026-04-14",
    payment_terms="Net 30",
    currency="USD",
    line_items=[],
    subtotal=9000.00,
    tax_rate=8.5,
    tax_amount=765.00,
    total=9765.00,
    amount_due=9765.00,
    confidence=0.95,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
@patch("src.docextract.app.extract_from_text", new_callable=AsyncMock)
async def test_extract_text_file(mock_extract):
    mock_extract.return_value = MOCK_EXTRACTION

    with open(SAMPLE_INVOICE_PATH, "rb") as f:
        content = f.read()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/extract",
            files={"file": ("invoice.txt", content, "text/plain")},
            headers={"x-api-key": "test-key"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["vendor_name"] == "Acme Software Solutions"
    assert body["data"]["total"] == 9765.00


@pytest.mark.anyio
async def test_extract_unsupported_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/extract",
            files={"file": ("data.xml", b"<xml/>", "application/xml")},
            headers={"x-api-key": "test-key"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Unsupported file type" in body["error"]


@pytest.mark.anyio
async def test_missing_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/extract",
            files={"file": ("invoice.txt", b"test", "text/plain")},
        )

    assert resp.status_code == 422  # Missing required header
