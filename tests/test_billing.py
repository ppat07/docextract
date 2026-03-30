"""Tests for SQLite-backed billing persistence."""
import os
import tempfile

import pytest

# Point DB to a temp file before importing billing
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DOCEXTRACT_DB_PATH"] = _tmp.name

from src.docextract.billing import (
    create_customer,
    get_usage,
    record_usage,
    validate_billing_key,
)


@pytest.fixture(autouse=True)
def clean_db():
    """Reset the DB between tests."""
    from src.docextract.billing import _get_db
    db = _get_db()
    db.execute("DELETE FROM usage_records")
    db.execute("DELETE FROM customers")
    db.commit()
    db.close()
    yield


@pytest.mark.anyio
async def test_create_and_validate_customer():
    result = await create_customer("test@example.com")
    assert result["api_key"].startswith("dex_")
    assert result["email"] == "test@example.com"
    assert validate_billing_key(result["api_key"])


@pytest.mark.anyio
async def test_unknown_key_rejected():
    assert not validate_billing_key("dex_nonexistent")


@pytest.mark.anyio
async def test_usage_tracking():
    result = await create_customer("user@example.com")
    key = result["api_key"]

    usage = get_usage(key)
    assert usage["documents_processed"] == 0

    await record_usage(key)
    await record_usage(key)
    await record_usage(key)

    usage = get_usage(key)
    assert usage["documents_processed"] == 3
    assert usage["estimated_charges"] == 0.75


@pytest.mark.anyio
async def test_persistence_across_connections():
    """Data survives closing and reopening the DB."""
    result = await create_customer("persist@example.com")
    key = result["api_key"]
    await record_usage(key)

    # Validate from a fresh connection
    assert validate_billing_key(key)
    usage = get_usage(key)
    assert usage["documents_processed"] == 1
