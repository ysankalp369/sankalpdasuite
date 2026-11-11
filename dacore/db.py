"""Database models (SQLAlchemy 2.x). Works with SQLite and PostgreSQL."""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, String, Text,
                        create_engine, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # pragma: no cover - driver hook
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class SessionToken(Base):
    __tablename__ = "session_tokens"
    token: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), default="intake")
    # Master project database: {field_key: {"value":..,"status":..,"sources":[..],"note":..}}
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, onupdate=now)

    documents: Mapped[list["Document"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    units: Mapped[list["Unit"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    category: Mapped[str] = mapped_column(String(40))        # society/property/members/developer/technical/review/reference
    doc_type: Mapped[str] = mapped_column(String(80), default="unclassified")
    filename: Mapped[str] = mapped_column(String(400))
    stored_name: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str] = mapped_column(String(120), default="")
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)   # extracted document-level metadata
    text_index: Mapped[list[Any]] = mapped_column(JSON, default=list)  # [{"page":..,"para":..,"text":..}]
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    project: Mapped[Project | None] = relationship(back_populates="documents")


class Fact(Base):
    """One extracted fact, always tied to its source location."""
    __tablename__ = "facts"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    field: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(Text)
    normalized: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(String(20), default="rule")  # rule | ai | table
    confidence: Mapped[float] = mapped_column(default=0.8)
    category: Mapped[str] = mapped_column(String(20), default="legal")  # legal/technical/commercial/member


class Unit(Base):
    """An existing flat/shop. Members are holders of units – never assume 1 unit = 1 member."""
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    unit_no: Mapped[str] = mapped_column(String(60))
    building: Mapped[str] = mapped_column(String(60), default="")
    floor: Mapped[str] = mapped_column(String(40), default="")
    unit_type: Mapped[str] = mapped_column(String(60), default="")
    use: Mapped[str] = mapped_column(String(20), default="Residential")
    holders: Mapped[list[Any]] = mapped_column(JSON, default=list)  # [{"name","share","status","pan_on_file"}]
    existing_rera_carpet_sqft: Mapped[float | None] = mapped_column(nullable=True)
    existing_mofa_carpet_sqft: Mapped[float | None] = mapped_column(nullable=True)
    existing_builtup_sqft: Mapped[float | None] = mapped_column(nullable=True)
    new_rera_carpet_sqft: Mapped[float | None] = mapped_column(nullable=True)
    balcony_sqft: Mapped[float | None] = mapped_column(nullable=True)
    additional_purchased_sqft: Mapped[float | None] = mapped_column(nullable=True)
    parking: Mapped[str] = mapped_column(String(80), default="")
    monthly_rent: Mapped[float | None] = mapped_column(nullable=True)
    deposit: Mapped[float | None] = mapped_column(nullable=True)
    brokerage: Mapped[float | None] = mapped_column(nullable=True)
    shifting: Mapped[float | None] = mapped_column(nullable=True)
    corpus: Mapped[float | None] = mapped_column(nullable=True)
    hardship: Mapped[float | None] = mapped_column(nullable=True)
    share_cert_no: Mapped[str] = mapped_column(String(60), default="")
    consent: Mapped[str] = mapped_column(String(20), default="unknown")   # given / refused / unknown
    mortgage: Mapped[str] = mapped_column(String(200), default="")
    bank_noc: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(60), default="regular")   # regular / deceased-heirship / transfer-pending / dispute
    society_dues: Mapped[float | None] = mapped_column(nullable=True)
    sources: Mapped[list[Any]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    project: Mapped[Project] = relationship(back_populates="units")


class Clause(Base):
    """Clause library entry."""
    __tablename__ = "clauses"
    id: Mapped[int] = mapped_column(primary_key=True)
    clause_code: Mapped[str] = mapped_column(String(40), unique=True)
    subject: Mapped[str] = mapped_column(String(200))
    article: Mapped[str] = mapped_column(String(120), default="")
    standard_wording: Mapped[str] = mapped_column(Text, default="")
    alternative_wording: Mapped[str] = mapped_column(Text, default="")
    society_favourable: Mapped[str] = mapped_column(Text, default="")
    neutral_version: Mapped[str] = mapped_column(Text, default="")
    source_agreement: Mapped[str] = mapped_column(String(300), default="")
    legal_provision: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    risk_addressed: Mapped[str] = mapped_column(Text, default="")
    recommended_use: Mapped[str] = mapped_column(Text, default="")
    related: Mapped[list[Any]] = mapped_column(JSON, default=list)
    classification: Mapped[str] = mapped_column(String(40), default="Negotiable")
    # approved / pending_review / rejected. Only 'approved' may be used as a standard.
    approval_status: Mapped[str] = mapped_column(String(30), default="pending_review")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    contains_project_facts: Mapped[bool] = mapped_column(Boolean, default=False)
    topic: Mapped[str] = mapped_column(String(60), default="general")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class LegalSource(Base):
    """Register of statutes / circulars / judgments with verification status."""
    __tablename__ = "legal_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(40))  # statute / rules / circular / regulation / judgment
    provision: Mapped[str] = mapped_column(String(200), default="")
    proposition: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(Text, default="")
    effective_version: Mapped[str] = mapped_column(String(200), default="")
    verified_on: Mapped[str] = mapped_column(String(40), default="")
    verification_status: Mapped[str] = mapped_column(String(40), default="advocate verification required")
    topics: Mapped[list[Any]] = mapped_column(JSON, default=list)


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), nullable=True)
    kind: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(300))
    stored_name: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="draft")  # draft / finalised
    sensitive: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    findings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(80), default="system")
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


def init_db() -> None:
    Base.metadata.create_all(engine)
