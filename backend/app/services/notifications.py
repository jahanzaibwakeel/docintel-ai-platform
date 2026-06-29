from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    kind: str,
    title: str,
    message: str,
    workspace_id: int | None = None,
    document_id: int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        workspace_id=workspace_id,
        document_id=document_id,
        kind=kind,
        title=title,
        message=message,
    )
    db.add(notification)
    return notification


def notify_document_ready(db: Session, document: Document) -> None:
    create_notification(
        db,
        user_id=document.owner_id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        kind="document.ready",
        title="Document ready",
        message=f"{document.filename} has finished processing.",
    )


def notify_document_failed(db: Session, document: Document) -> None:
    create_notification(
        db,
        user_id=document.owner_id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        kind="document.failed",
        title="Document processing failed",
        message=f"{document.filename} failed: {document.error_message or 'Unknown error'}",
    )
