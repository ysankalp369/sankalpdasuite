"""Authentication, role-based permissions, encryption at rest and audit trail."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from .config import INSTANCE_DIR, SESSION_HOURS
from .db import AuditLog, SessionToken, User, now

ROLES = {
    "super_admin": "Super Administrator",
    "legal_head": "Advocate / Legal Head",
    "junior_advocate": "Junior Advocate",
    "pmc_admin": "PMC Administrator",
    "project_engineer": "Project Engineer",
    "document_manager": "Document Manager",
}

# permission -> roles allowed
PERMISSIONS = {
    "project.create": {"super_admin", "legal_head", "junior_advocate", "pmc_admin"},
    "project.edit": {"super_admin", "legal_head", "junior_advocate", "pmc_admin", "project_engineer"},
    "project.delete": {"super_admin"},
    "document.upload": set(ROLES),
    "document.view": set(ROLES),
    "draft.generate": {"super_admin", "legal_head", "junior_advocate"},
    "draft.finalise": {"super_admin", "legal_head"},
    "review.run": {"super_admin", "legal_head", "junior_advocate"},
    "clause.propose": {"super_admin", "legal_head", "junior_advocate"},
    "clause.approve": {"super_admin", "legal_head"},
    "download.sensitive": {"super_admin", "legal_head", "pmc_admin"},
    "download.draft": {"super_admin", "legal_head", "junior_advocate", "pmc_admin"},
    "users.manage": {"super_admin"},
    "audit.view": {"super_admin", "legal_head", "pmc_admin"},
    "legal.edit": {"super_admin", "legal_head"},
}


def can(user: User | None, perm: str) -> bool:
    return bool(user and user.active and user.role in PERMISSIONS.get(perm, set()))


# ---------------------------------------------------------------- passwords
def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 310_000)
    return f"pbkdf2${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 310_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


def create_session(db: Session, user: User) -> str:
    tok = secrets.token_urlsafe(32)
    db.add(SessionToken(token=tok, user_id=user.id, expires_at=now() + dt.timedelta(hours=SESSION_HOURS)))
    db.commit()
    return tok


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    st = db.get(SessionToken, token)
    if not st or st.expires_at < now():
        return None
    u = db.get(User, st.user_id)
    return u if u and u.active else None


def ensure_bootstrap_admin(db: Session) -> str | None:
    """Create the first Super Administrator; credentials are written to instance/ only."""
    if db.query(User).count():
        return None
    pw = secrets.token_urlsafe(12)
    db.add(User(username="admin", full_name="Super Administrator", role="super_admin",
                password_hash=hash_password(pw)))
    db.commit()
    cred = INSTANCE_DIR / "initial_admin_credentials.txt"
    cred.write_text(
        "Initial Super Administrator account (change the password after first login)\n"
        f"username: admin\npassword: {pw}\n", encoding="utf-8")
    return str(cred)


# ---------------------------------------------------------------- encryption at rest
_KEY_FILE = INSTANCE_DIR / "storage.key"


def _fernet() -> Fernet:
    key = os.environ.get("DA_STORAGE_KEY")
    if not key:
        if not _KEY_FILE.exists():
            _KEY_FILE.write_bytes(Fernet.generate_key())
        key = _KEY_FILE.read_bytes().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def write_encrypted(path: Path, data: bytes) -> None:
    path.write_bytes(_fernet().encrypt(data))


def read_encrypted(path: Path) -> bytes:
    return _fernet().decrypt(path.read_bytes())


# ---------------------------------------------------------------- audit
def audit(db: Session, user: User | None, action: str, project_id: int | None = None, **detail) -> None:
    db.add(AuditLog(user_id=user.id if user else None, username=user.username if user else "system",
                    project_id=project_id, action=action, detail=detail))
    db.commit()
