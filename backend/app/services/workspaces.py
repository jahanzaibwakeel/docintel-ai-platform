from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


def create_personal_workspace(db: Session, user: User) -> Workspace:
    workspace = Workspace(name=f"{user.full_name}'s Workspace")
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner))
    return workspace


def get_user_workspaces(db: Session, user_id: int) -> list[Workspace]:
    return list(
        db.scalars(
            select(Workspace)
            .join(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.asc(), Workspace.id.asc())
        )
    )


def get_default_workspace(db: Session, user: User) -> Workspace:
    workspace = db.scalar(
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.asc(), Workspace.id.asc())
    )
    if workspace:
        return workspace
    return create_personal_workspace(db, user)


def require_workspace_member(db: Session, user: User, workspace_id: int) -> WorkspaceMember:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You do not have access to this workspace")
    return membership


def require_workspace_writer(db: Session, user: User, workspace_id: int) -> WorkspaceMember:
    membership = require_workspace_member(db, user, workspace_id)
    if membership.role == WorkspaceRole.viewer:
        raise HTTPException(status_code=403, detail="Viewer access cannot modify this workspace")
    return membership


def workspace_usage(db: Session, workspace_id: int) -> dict:
    row = db.execute(
        select(
            func.count(Document.id).label("document_count"),
            func.coalesce(func.sum(Document.page_count), 0).label("page_count"),
            func.coalesce(func.sum(Document.file_size_bytes), 0).label("storage_bytes"),
        ).where(Document.workspace_id == workspace_id, Document.status != DocumentStatus.deleted)
    ).one()
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    storage_mb = round((row.storage_bytes or 0) / (1024 * 1024), 2)

    def percent(value: int | float, quota: int | None) -> float | None:
        return round((value / quota) * 100, 2) if quota else None

    return {
        "workspace_id": workspace_id,
        "document_count": row.document_count or 0,
        "page_count": row.page_count or 0,
        "storage_bytes": row.storage_bytes or 0,
        "storage_mb": storage_mb,
        "document_quota": workspace.document_quota,
        "page_quota": workspace.page_quota,
        "storage_quota_mb": workspace.storage_quota_mb,
        "document_quota_used_percent": percent(row.document_count or 0, workspace.document_quota),
        "page_quota_used_percent": percent(row.page_count or 0, workspace.page_quota),
        "storage_quota_used_percent": percent(storage_mb, workspace.storage_quota_mb),
    }


def assert_workspace_upload_quota(db: Session, workspace: Workspace, incoming_bytes: int) -> None:
    usage = workspace_usage(db, workspace.id)
    if workspace.document_quota is not None and usage["document_count"] >= workspace.document_quota:
        raise HTTPException(status_code=409, detail="Workspace document quota exceeded")
    if workspace.storage_quota_mb is not None:
        next_storage_mb = (usage["storage_bytes"] + incoming_bytes) / (1024 * 1024)
        if next_storage_mb > workspace.storage_quota_mb:
            raise HTTPException(status_code=409, detail="Workspace storage quota exceeded")


def assert_workspace_page_quota(db: Session, workspace_id: int, document_id: int, incoming_pages: int) -> None:
    workspace = db.get(Workspace, workspace_id)
    if not workspace or workspace.page_quota is None:
        return
    existing_pages = db.scalar(
        select(func.coalesce(func.sum(Document.page_count), 0)).where(
            Document.workspace_id == workspace_id,
            Document.id != document_id,
            Document.status != DocumentStatus.deleted,
        )
    ) or 0
    if existing_pages + incoming_pages > workspace.page_quota:
        raise ValueError("Workspace page quota exceeded")
