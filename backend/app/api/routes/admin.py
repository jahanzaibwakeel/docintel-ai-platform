from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.admin import AdminDocumentResponse, AdminStatsResponse, AdminUserResponse, AdminWorkspaceResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    settings = get_settings()
    admin_emails = {email.strip().lower() for email in settings.admin_emails.split(",") if email.strip()}
    if current_user.email.lower() not in admin_emails:
        raise HTTPException(status_code=403, detail="Admin access is required")
    return current_user


@router.get("/stats", response_model=AdminStatsResponse)
def admin_stats(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminStatsResponse:
    status_counts = dict(
        db.execute(select(Document.status, func.count(Document.id)).group_by(Document.status)).all()
    )
    return AdminStatsResponse(
        users=db.scalar(select(func.count(User.id))) or 0,
        workspaces=db.scalar(select(func.count(Workspace.id))) or 0,
        documents=db.scalar(select(func.count(Document.id)).where(Document.status != DocumentStatus.deleted)) or 0,
        ready_documents=status_counts.get(DocumentStatus.ready, 0),
        failed_documents=status_counts.get(DocumentStatus.failed, 0),
        processing_documents=status_counts.get(DocumentStatus.processing, 0),
        uploaded_documents=status_counts.get(DocumentStatus.uploaded, 0),
    )


@router.get("/users", response_model=list[AdminUserResponse])
def admin_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminUserResponse]:
    rows = db.execute(
        select(
            User.id,
            User.email,
            User.full_name,
            User.created_at,
            func.count(func.distinct(WorkspaceMember.workspace_id)).label("workspace_count"),
            func.count(func.distinct(Document.id)).label("document_count"),
        )
        .outerjoin(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .outerjoin(Document, Document.owner_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc(), User.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminUserResponse(
            id=row.id,
            email=row.email,
            full_name=row.full_name,
            created_at=row.created_at,
            workspace_count=row.workspace_count,
            document_count=row.document_count,
        )
        for row in rows
    ]


@router.get("/workspaces", response_model=list[AdminWorkspaceResponse])
def admin_workspaces(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminWorkspaceResponse]:
    rows = db.execute(
        select(
            Workspace.id,
            Workspace.name,
            Workspace.created_at,
            func.count(func.distinct(WorkspaceMember.id)).label("member_count"),
            func.count(func.distinct(Document.id)).label("document_count"),
        )
        .outerjoin(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .outerjoin(Document, Document.workspace_id == Workspace.id)
        .group_by(Workspace.id)
        .order_by(Workspace.created_at.desc(), Workspace.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminWorkspaceResponse(
            id=row.id,
            name=row.name,
            created_at=row.created_at,
            member_count=row.member_count,
            document_count=row.document_count,
        )
        for row in rows
    ]


@router.get("/documents", response_model=list[AdminDocumentResponse])
def admin_documents(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    status: DocumentStatus | None = Query(default=None),
    failed_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminDocumentResponse]:
    statement = (
        select(Document, User.email)
        .outerjoin(User, User.id == Document.owner_id)
        .where(Document.status != DocumentStatus.deleted)
        .order_by(
            case((Document.status == DocumentStatus.failed, 0), else_=1),
            Document.created_at.desc(),
            Document.id.desc(),
        )
        .limit(limit)
    )
    if failed_only:
        statement = statement.where(Document.status == DocumentStatus.failed)
    elif status is not None:
        statement = statement.where(Document.status == status)

    rows = db.execute(statement).all()
    return [
        AdminDocumentResponse(
            id=document.id,
            filename=document.filename,
            owner_email=email,
            workspace_id=document.workspace_id,
            status=document.status,
            document_type=document.document_type,
            error_message=document.error_message,
            created_at=document.created_at,
            processing_started_at=document.processing_started_at,
            processing_completed_at=document.processing_completed_at,
        )
        for document, email in rows
    ]
