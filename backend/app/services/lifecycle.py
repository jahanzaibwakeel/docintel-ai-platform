from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentChunk, DocumentMessage, DocumentStatus
from app.services.audit import log_action
from app.services.storage import get_storage


def apply_default_retention(document: Document) -> None:
    settings = get_settings()
    if settings.default_retention_days > 0:
        document.retention_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.default_retention_days)


def delete_document(db: Session, document: Document, actor_id: int | None, reason: str) -> None:
    get_storage().delete(document.storage_path)

    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    db.execute(delete(DocumentMessage).where(DocumentMessage.document_id == document.id))

    document.status = DocumentStatus.deleted
    document.deleted_at = datetime.now(timezone.utc)
    document.deleted_by_id = actor_id
    document.extracted_text = None
    document.summary = None
    document.key_fields = None
    document.structured_fields = None
    document.risk_flags = None
    document.extraction_diagnostics = None
    document.error_message = None
    document.storage_path = ""
    log_action(
        db,
        action="document.delete",
        actor_id=actor_id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        metadata={"reason": reason},
    )


def cleanup_expired_documents(db: Session, limit: int = 100) -> int:
    now = datetime.now(timezone.utc)
    documents = list(
        db.scalars(
            select(Document)
            .where(
                Document.retention_expires_at.is_not(None),
                Document.retention_expires_at <= now,
                Document.status != DocumentStatus.deleted,
            )
            .order_by(Document.retention_expires_at.asc())
            .limit(limit)
        )
    )
    for document in documents:
        delete_document(db, document, actor_id=None, reason="retention_expired")
    return len(documents)
