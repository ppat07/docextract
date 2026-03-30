import io
import os
import traceback
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PyPDF2 import PdfReader

from .billing import (
    create_customer,
    get_usage,
    record_usage,
    validate_billing_key,
)
from .config import DOCEXTRACT_API_KEYS, MAX_FILE_SIZE_MB
from .extractor import extract_from_image, extract_from_text
from .models import ExtractionResponse

app = FastAPI(
    title="DocExtract",
    description="AI-powered invoice and receipt data extraction API",
    version="0.2.0",
)

IMAGE_TYPES = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}

PDF_TYPES = {"application/pdf"}

STATIC_DIR = Path(os.environ.get("DOCEXTRACT_STATIC_DIR", Path(__file__).resolve().parent.parent.parent / "static"))


def verify_api_key(x_api_key: str = Header(...)) -> str:
    # Accept keys from the env-configured set OR from billing-provisioned keys
    if not DOCEXTRACT_API_KEYS and not validate_billing_key(x_api_key):
        return x_api_key  # No keys configured and not a billing key = open access (dev mode)
    if x_api_key in DOCEXTRACT_API_KEYS or validate_billing_key(x_api_key):
        return x_api_key
    raise HTTPException(status_code=401, detail="Invalid API key")


# --------------- Landing page ---------------

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>DocExtract</h1><p>API is running.</p>")


# --------------- Health ---------------

@app.get("/health")
async def health():
    return {"status": "ok"}


# --------------- Core extraction ---------------

@app.post("/extract", response_model=ExtractionResponse)
async def extract_document(
    file: UploadFile,
    _key: str = Depends(verify_api_key),
) -> ExtractionResponse:
    """Upload an invoice/receipt (PDF or image) and get structured JSON back."""
    content = await file.read()

    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        return ExtractionResponse(
            success=False,
            error=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
        )

    content_type = file.content_type or ""

    try:
        if content_type in IMAGE_TYPES:
            result = await extract_from_image(content, IMAGE_TYPES[content_type])
        elif content_type in PDF_TYPES:
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                return ExtractionResponse(
                    success=False,
                    error="Could not extract text from PDF. Try uploading as an image.",
                )
            result = await extract_from_text(text)
        elif content_type.startswith("text/"):
            result = await extract_from_text(content.decode("utf-8"))
        else:
            return ExtractionResponse(
                success=False,
                error=f"Unsupported file type: {content_type}. Supported: PDF, PNG, JPEG, GIF, WEBP, plain text.",
            )

        # Track usage for billing
        await record_usage(_key)

        return ExtractionResponse(success=True, data=result)

    except Exception:
        return ExtractionResponse(
            success=False,
            error=f"Extraction failed: {traceback.format_exc()}",
        )


# --------------- Billing / Customer endpoints ---------------

class SignupRequest(BaseModel):
    email: str


@app.post("/billing/signup")
async def billing_signup(req: SignupRequest):
    """Create a new customer and provision an API key."""
    result = await create_customer(req.email)
    return {
        "success": True,
        "api_key": result["api_key"],
        "customer_id": result["customer_id"],
        "message": "Save your API key — it won't be shown again.",
    }


@app.get("/billing/usage")
async def billing_usage(x_api_key: str = Header(...)):
    """Check usage and estimated charges for your API key."""
    return get_usage(x_api_key)
