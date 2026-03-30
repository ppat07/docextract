from __future__ import annotations

import os
from typing import Set

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DOCEXTRACT_API_KEYS: Set[str] = set(
    k.strip()
    for k in os.environ.get("DOCEXTRACT_API_KEYS", "").split(",")
    if k.strip()
)
MAX_FILE_SIZE_MB = int(os.environ.get("DOCEXTRACT_MAX_FILE_SIZE_MB", "10"))
MODEL = os.environ.get("DOCEXTRACT_MODEL", "claude-sonnet-4-20250514")
DATABASE_PATH = os.environ.get("DOCEXTRACT_DB_PATH", "/tmp/docextract.db")
