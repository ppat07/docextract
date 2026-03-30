"""Usage-based billing with Stripe (metered).

When STRIPE_SECRET_KEY is not set, billing is stubbed:
- All API-key checks pass
- Usage is tracked locally only
- /billing/usage returns the local counter

When STRIPE_SECRET_KEY is set, full Stripe metered billing is active.

Customer and usage data is persisted in SQLite so it survives restarts.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

import stripe

from .config import DATABASE_PATH

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")  # metered price
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

stripe.api_key = STRIPE_SECRET_KEY

# --------------- SQLite persistence ---------------

def _get_db() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            api_key TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            subscription_id TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at REAL NOT NULL DEFAULT (unixepoch('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            api_key TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (api_key),
            FOREIGN KEY (api_key) REFERENCES customers(api_key)
        )
    """)
    conn.commit()
    return conn


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

    db = _get_db()
    try:
        db.execute(
            "INSERT INTO customers (api_key, customer_id, subscription_id, email) VALUES (?, ?, ?, ?)",
            (api_key, record["customer_id"], record["subscription_id"], record["email"]),
        )
        db.execute(
            "INSERT INTO usage_records (api_key, count) VALUES (?, 0)",
            (api_key,),
        )
        db.commit()
    finally:
        db.close()

    return {"api_key": api_key, **record}


async def record_usage(api_key: str) -> None:
    """Record one document extraction for billing."""
    db = _get_db()
    try:
        db.execute(
            "INSERT INTO usage_records (api_key, count) VALUES (?, 1) ON CONFLICT(api_key) DO UPDATE SET count = count + 1",
            (api_key,),
        )
        db.commit()
    finally:
        db.close()

    if is_stripe_live():
        db = _get_db()
        try:
            row = db.execute("SELECT subscription_id FROM customers WHERE api_key = ?", (api_key,)).fetchone()
        finally:
            db.close()
        if row:
            sub_id = row["subscription_id"]
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
    db = _get_db()
    try:
        row = db.execute("SELECT count FROM usage_records WHERE api_key = ?", (api_key,)).fetchone()
    finally:
        db.close()
    docs = row["count"] if row else 0
    return {
        "api_key": api_key[:8] + "...",
        "documents_processed": docs,
        "price_per_document": 0.25,
        "estimated_charges": round(docs * 0.25, 2),
        "billing_mode": "stripe" if is_stripe_live() else "stub",
    }


def validate_billing_key(api_key: str) -> bool:
    """Check if an API key is known to the billing system."""
    db = _get_db()
    try:
        row = db.execute("SELECT 1 FROM customers WHERE api_key = ?", (api_key,)).fetchone()
    finally:
        db.close()
    return row is not None
