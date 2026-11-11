"""Application configuration.

All settings can be overridden by environment variables so that the same code
runs on a laptop (SQLite) or a server (PostgreSQL).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = Path(os.environ.get("DA_INSTANCE_DIR", BASE_DIR / "instance"))
STORAGE_DIR = INSTANCE_DIR / "storage"          # encrypted project documents
OUTPUT_DIR = INSTANCE_DIR / "outputs"           # generated documents (encrypted)
for _d in (INSTANCE_DIR, STORAGE_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# SQLite by default; set DATABASE_URL=postgresql+psycopg://user:pass@host/db for PostgreSQL.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'da_suite.db').as_posix()}")

# Claude API (optional). Without credentials the deterministic engines still run.
CLAUDE_MODEL = os.environ.get("DA_CLAUDE_MODEL", "claude-opus-5-5")
AI_ENABLED = os.environ.get("DA_AI_ENABLED", "auto")  # auto | on | off

# Session lifetime for logged-in users (hours)
SESSION_HOURS = int(os.environ.get("DA_SESSION_HOURS", "12"))

# Retention: generated outputs older than this many days may be purged by an admin.
RETENTION_DAYS = int(os.environ.get("DA_RETENTION_DAYS", "1825"))

FIRM_LEGAL = "Adv. Santosh Yadav Associates – Legal Advisory"
FIRM_PMC = "Sankalp Project Management Consultants Pvt. Ltd."
REVIEW_AUTHOR = os.environ.get("DA_REVIEW_AUTHOR", "SYA Legal Review")
