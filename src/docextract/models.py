from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class ExtractedInvoice(BaseModel):
    document_type: str
    vendor_name: Optional[str] = None
    vendor_address: Optional[Address] = None
    customer_name: Optional[str] = None
    customer_address: Optional[Address] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = None
    line_items: List[LineItem] = []
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    amount_due: Optional[float] = None
    notes: Optional[str] = None
    confidence: float


class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[ExtractedInvoice] = None
    error: Optional[str] = None
    usage: Optional[dict] = None
