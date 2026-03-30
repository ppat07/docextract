"""Usage-based billing with Stripe (metered).

When STRIPE_SECRET_KEY is not set, billing is stubbed:
- All API-key checks pass
- Usage is tracked in-memory only
- /billing/usage returns the in-memory counter

When STRIPE_SECRET_KEY is set, full Stripe metered billing is active.
"""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict
from typing import Optional

import stripe

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")  # metered price
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

stripe.api_key = STRIPE_SECRET_KEY

# In-memory store (replaced by a DB in production)
_customers: dict[str, dict] = {}  # api_key -> {customer_id, subscription_id, email}
_usage: dict[str, int] = defaultdict(int)  # api_key -> doc count


def is_stripe_live() -> bool:
    return bool(STRIPE_SECRET_KEY)


def generate_api_key() -> str:
    return f"dex_{secrets.token_urlsafe(32)}"


async def create_customer(email: str) -> dict:
    """Provision a new customer with an API key.

    Returns {"api_key": ..., "customer_id": ..., "email": ...}.
    """
    api_key = generate_api_key()

    if is_stripe_live():
        customer = stripe.Customer.create(email=email)
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": STRIPE_PRICE_ID}],
        )
        record = {
            "customer_id": customer.id,
            "subscription_id": subscription.id,
            "email": email,
        }
    else:
        record = {
            "customer_id": f"cus_stub_{secrets.token_hex(8)}",
            "subscription_id": f"sub_stub_{secrets.token_hex(8)}",
            "email": email,
        }

    _customers[api_key] = record
    return {"api_key": api_key, **record}


async def record_usage(api_key: str) -> None:
    """Record one document extraction for billing."""
    _usage[api_key] += 1

    if is_stripe_live() and api_key in _customers:
        sub_id = _customers[api_key]["subscription_id"]
        subscription = stripe.Subscription.retrieve(sub_id)
        si_id = subscription["items"]["data"][0]["id"]
        stripe.SubscriptionItem.create_usage_record(
            si_id,
            quantity=1,
            timestamp=int(time.time()),
            action="increment",
        )


def get_usage(api_key: str) -> dict:
    """Return usage stats for an API key."""
    return {
        "api_key": api_key[:8] + "...",
        "documents_processed": _usage.get(api_key, 0),
        "price_per_document": 0.25,
        "estimated_charges": round(_usage.get(api_key, 0) * 0.25, 2),
        "billing_mode": "stripe" if is_stripe_live() else "stub",
    }


def validate_billing_key(api_key: str) -> bool:
    """Check if an API key is known to the billing system."""
    return api_key in _customers
