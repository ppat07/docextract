import base64
import json
import re

import anthropic

from .config import ANTHROPIC_API_KEY, MODEL
from .models import ExtractedInvoice

EXTRACTION_PROMPT = """You are a precise document data extraction system. Extract structured data from the provided invoice, receipt, or bill.

Return a JSON object with these fields (use null for any field you cannot find):

{
  "document_type": "invoice" | "receipt" | "bill" | "credit_note" | "purchase_order",
  "vendor_name": "string",
  "vendor_address": {"street": "", "city": "", "state": "", "zip_code": "", "country": ""},
  "customer_name": "string",
  "customer_address": {"street": "", "city": "", "state": "", "zip_code": "", "country": ""},
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "payment_terms": "string (e.g. Net 30)",
  "currency": "USD" | "EUR" | etc.,
  "line_items": [{"description": "", "quantity": 0.0, "unit_price": 0.0, "amount": 0.0}],
  "subtotal": 0.0,
  "tax_rate": 0.0,
  "tax_amount": 0.0,
  "discount": 0.0,
  "total": 0.0,
  "amount_due": 0.0,
  "notes": "any additional notes or payment instructions",
  "confidence": 0.0-1.0
}

Rules:
- All monetary values should be numbers (not strings)
- Dates in YYYY-MM-DD format
- Set confidence between 0.0-1.0 based on how clearly the data was readable
- If the document is not an invoice/receipt/bill, set confidence to 0.0 and document_type to the best guess
- Return ONLY the JSON object, no other text"""


client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def extract_from_text(text: str) -> ExtractedInvoice:
    """Extract invoice data from plain text content."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\nDocument text:\n\n{text}",
            }
        ],
    )
    return _parse_response(response)


async def extract_from_image(
    image_data: bytes, media_type: str
) -> ExtractedInvoice:
    """Extract invoice data from an image (PNG, JPEG, GIF, WEBP)."""
    b64 = base64.standard_b64encode(image_data).decode("utf-8")
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )
    return _parse_response(response)


def _parse_response(response: anthropic.types.Message) -> ExtractedInvoice:
    """Parse Claude's response into a structured ExtractedInvoice."""
    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    data = json.loads(raw)
    return ExtractedInvoice(**data)
