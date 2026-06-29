from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

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

