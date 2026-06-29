from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.database import Base


class DocumentStatus(StrEnum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"
    deleted = "deleted"


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


class DocumentReviewStatus(StrEnum):
    unreviewed = "unreviewed"
    in_review = "in_review"
    approved = "approved"
    needs_changes = "needs_changes"


class DocumentCollection(Base):
    __tablename__ = "document_collections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documents = relationship("Document", back_populates="collection")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("document_collections.id", ondelete="SET NULL"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    title: Mapped[str | None] = mapped_column(String(512), index=True)
    content_type: Mapped[str] = mapped_column(String(128), default="application/pdf")
    storage_path: Mapped[str] = mapped_column(String(1024))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.uploaded, index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    key_fields: Mapped[dict | None] = mapped_column(JSONB)
    document_type: Mapped[str | None] = mapped_column(String(80), index=True)
    document_type_confidence: Mapped[int | None] = mapped_column(Integer)
    structured_fields: Mapped[dict | None] = mapped_column(JSONB)
    risk_flags: Mapped[list | None] = mapped_column(JSONB)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    review_status: Mapped[DocumentReviewStatus] = mapped_column(Enum(DocumentReviewStatus), default=DocumentReviewStatus.unreviewed, nullable=False, index=True)
    review_notes: Mapped[str | None] = mapped_column(Text)
    extraction_diagnostics: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="documents", foreign_keys=[owner_id])
    workspace = relationship("Workspace", back_populates="documents")
    collection = relationship("DocumentCollection", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    messages = relationship("DocumentMessage", back_populates="document", cascade="all, delete-orphan")
    annotations = relationship("DocumentAnnotation", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(get_settings().embedding_dimensions))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")


class DocumentMessage(Base):
    __tablename__ = "document_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), index=True)
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="messages")


class DocumentAnnotation(Base):
    __tablename__ = "document_annotations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    quote_text: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document = relationship("Document", back_populates="annotations")
