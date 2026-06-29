from sqlalchemy.orm import Session

from app.models.workspace import AuditLog


def log_action(
    db: Session,
    *,
    action: str,
    actor_id: int | None,
    workspace_id: int | None = None,
    document_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            actor_id=actor_id,
            workspace_id=workspace_id,
            document_id=document_id,
            details=metadata,
        )
    )
