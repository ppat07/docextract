# DocExtract

AI-powered invoice and receipt data extraction API. Upload a PDF, image, or text file of an invoice/receipt and get back clean, structured JSON.

## What it does

DocExtract uses Claude to read invoices, receipts, and bills and extract:

- Vendor and customer details (name, address)
- Invoice number, dates, payment terms
- Line items with descriptions, quantities, and amounts
- Subtotal, tax, discounts, and total
- Currency and payment instructions

## Quick start (local)

```bash
# 1. Clone and set up
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env with your Anthropic API key

# 3. Run
uvicorn src.docextract.app:app --reload --port 8000
```

Visit http://localhost:8000 for the landing page.

## Deploy with Docker

```bash
docker build -t docextract .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e STRIPE_SECRET_KEY=sk_live_... \
  -e STRIPE_PRICE_ID=price_... \
  docextract
```

### Deploy to Railway / Fly.io / Render

The included `Dockerfile` is production-ready. Set the environment variables in your provider's dashboard and deploy.

**Railway:** Connect the repo and set env vars. Railway auto-detects the Dockerfile.

**Fly.io:**
```bash
fly launch --dockerfile Dockerfile
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

**Render:** Create a new Web Service, point to the repo, select Docker, and add env vars.

## API Reference

### POST /extract

Upload a document and receive structured extracted data.

```bash
curl -X POST https://your-domain.com/extract \
  -H "x-api-key: YOUR_API_KEY" \
  -F "file=@invoice.pdf"
```

Supported formats: PDF, PNG, JPEG, GIF, WEBP, plain text. Max 10 MB.

**Response:**

```json
{
  "success": true,
  "data": {
    "document_type": "invoice",
    "vendor_name": "Acme Software Solutions",
    "vendor_address": {
      "street": "123 Innovation Drive, Suite 400",
      "city": "San Francisco",
      "state": "CA",
      "zip_code": "94105",
      "country": "United States"
    },
    "customer_name": "TechStart Inc.",
    "invoice_number": "INV-2026-0042",
    "invoice_date": "2026-03-15",
    "due_date": "2026-04-14",
    "payment_terms": "Net 30",
    "currency": "USD",
    "line_items": [
      {
        "description": "API Integration Service",
        "quantity": 40,
        "unit_price": 150.00,
        "amount": 6000.00
      }
    ],
    "subtotal": 9000.00,
    "tax_rate": 8.5,
    "tax_amount": 765.00,
    "total": 9765.00,
    "amount_due": 9765.00,
    "confidence": 0.95
  }
}
```

### POST /billing/signup

Create a new customer account and get an API key.

```bash
curl -X POST https://your-domain.com/billing/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

**Response:**

```json
{
  "success": true,
  "api_key": "dex_abc123...",
  "customer_id": "cus_...",
  "message": "Save your API key — it won't be shown again."
}
```

### GET /billing/usage

Check your usage and estimated charges.

```bash
curl https://your-domain.com/billing/usage \
  -H "x-api-key: YOUR_API_KEY"
```

**Response:**

```json
{
  "api_key": "dex_abc1...",
  "documents_processed": 42,
  "price_per_document": 0.25,
  "estimated_charges": 10.50,
  "billing_mode": "stripe"
}
```

### GET /health

```bash
curl https://your-domain.com/health
# {"status": "ok"}
```

### GET /

Landing page with product info, pricing, and API docs.

## Pricing

**$0.25 per document** — usage-based, no monthly minimum. Billed via Stripe metered billing.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) | — |
| `DOCEXTRACT_API_KEYS` | Comma-separated static API keys | (open access) |
| `DOCEXTRACT_MAX_FILE_SIZE_MB` | Maximum upload size in MB | 10 |
| `DOCEXTRACT_MODEL` | Claude model to use | claude-sonnet-4-20250514 |
| `STRIPE_SECRET_KEY` | Stripe secret key (enables billing) | (stubbed) |
| `STRIPE_PRICE_ID` | Stripe metered price ID | — |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | — |

When `STRIPE_SECRET_KEY` is not set, billing runs in stub mode — API keys are provisioned but charges are not created.

## Running tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Architecture

```
src/docextract/
├── app.py        # FastAPI application with all endpoints
├── billing.py    # Stripe metered billing + API key provisioning
├── config.py     # Environment configuration
├── extractor.py  # Claude-powered extraction logic
└── models.py     # Pydantic response models
static/
└── index.html    # Landing page
Dockerfile        # Production container
```

Stateless single-service architecture. Deploy behind any reverse proxy or on any cloud platform that supports Docker or Python.
