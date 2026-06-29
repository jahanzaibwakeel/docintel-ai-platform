import json

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import (
    create_workspace_invite_token,
    hash_workspace_invite_token,
    workspace_invite_expires_at,
)
from app.models.user import User
from app.models.workspace import AuditLog, Workspace, WorkspaceInvitation, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    AcceptWorkspaceInvitationRequest,
    AddMemberRequest,
    AuditLogResponse,
    CreateWorkspaceRequest,
    UpdateMemberRoleRequest,
    UpdateWorkspaceRequest,
    WorkspaceInvitationResponse,
    WorkspaceInvitationListResponse,
    WorkspaceInviteResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from app.schemas.document import AskResponse, WorkspaceAskRequest
from app.services.audit import log_action
from app.services.email import send_workspace_invitation_email, send_workspace_member_email
from app.services.workspace_qa import answer_workspace_question
from app.services.workspaces import get_user_workspaces, require_workspace_member

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def require_workspace_admin(db: Session, user: User, workspace_id: int) -> WorkspaceMember:
    membership = require_workspace_member(db, user, workspace_id)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(status_code=403, detail="Admin access is required")
    return membership


def count_workspace_owners(db: Session, workspace_id: int) -> int:
    return db.scalar(
        select(func.count(WorkspaceMember.id)).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == WorkspaceRole.owner,
        )
    ) or 0


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Workspace]:
    return get_user_workspaces(db, current_user.id)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    workspace = Workspace(name=payload.name)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role=WorkspaceRole.owner))
    log_action(db, action="workspace.create", actor_id=current_user.id, workspace_id=workspace.id)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    payload: UpdateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    require_workspace_admin(db, current_user, workspace_id)
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    previous_name = workspace.name
    workspace.name = payload.name
    log_action(
        db,
        action="workspace.update",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"previous_name": previous_name, "name": workspace.name},
    )
    db.commit()
    db.refresh(workspace)
    return workspace


@router.post("/{workspace_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    membership = require_workspace_member(db, current_user, workspace_id)
    if membership.role == WorkspaceRole.owner and count_workspace_owners(db, workspace_id) <= 1:
        raise HTTPException(status_code=409, detail="A workspace must keep at least one owner")

    role = membership.role
    db.delete(membership)
    log_action(
        db,
        action="workspace.leave",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"role": role},
    )
    db.commit()


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
def list_members(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkspaceMember]:
    require_workspace_member(db, current_user, workspace_id)
    return list(db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id).order_by(WorkspaceMember.id.asc())))


@router.patch("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberResponse)
def update_member_role(
    workspace_id: int,
    member_id: int,
    payload: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMember:
    require_workspace_admin(db, current_user, workspace_id)
    membership = db.get(WorkspaceMember, member_id)
    if not membership or membership.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    if membership.role == WorkspaceRole.owner and payload.role != WorkspaceRole.owner and count_workspace_owners(db, workspace_id) <= 1:
        raise HTTPException(status_code=409, detail="A workspace must keep at least one owner")

    previous_role = membership.role
    membership.role = payload.role
    log_action(
        db,
        action="workspace.member_role_update",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"member_user_id": membership.user_id, "previous_role": previous_role, "role": payload.role},
    )
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    require_workspace_admin(db, current_user, workspace_id)
    membership = db.get(WorkspaceMember, member_id)
    if not membership or membership.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    if membership.role == WorkspaceRole.owner and count_workspace_owners(db, workspace_id) <= 1:
        raise HTTPException(status_code=409, detail="A workspace must keep at least one owner")

    removed_user_id = membership.user_id
    removed_role = membership.role
    db.delete(membership)
    log_action(
        db,
        action="workspace.member_remove",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"member_user_id": removed_user_id, "role": removed_role},
    )
    db.commit()


@router.post("/{workspace_id}/members", response_model=WorkspaceInviteResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: int,
    payload: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceInviteResponse:
    require_workspace_admin(db, current_user, workspace_id)
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        raw_token = create_workspace_invite_token()
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=payload.email.lower(),
            role=payload.role,
            token_hash=hash_workspace_invite_token(raw_token),
            invited_by_id=current_user.id,
            expires_at=workspace_invite_expires_at(),
        )
        db.add(invitation)
        log_action(
            db,
            action="workspace.invitation_create",
            actor_id=current_user.id,
            workspace_id=workspace_id,
            metadata={"email": payload.email.lower(), "role": payload.role},
        )
        db.commit()
        db.refresh(invitation)
        send_workspace_invitation_email(payload.email.lower(), workspace.name, payload.role.value, current_user.email, raw_token)
        return WorkspaceInviteResponse(status="invited", invitation=invitation)
    existing = db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id))
    previous_role = existing.role if existing else None
    if existing:
        existing.role = payload.role
        membership = existing
    else:
        membership = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=payload.role)
        db.add(membership)
    log_action(
        db,
        action="workspace.member_upsert",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"member_user_id": user.id, "role": payload.role, "previous_role": previous_role},
    )
    db.commit()
    db.refresh(membership)
    if user.id != current_user.id:
        send_workspace_member_email(user.email, workspace.name, payload.role.value, current_user.email)
    return WorkspaceInviteResponse(status="member", member=membership)


@router.post("/invitations/accept", response_model=WorkspaceMemberResponse)
def accept_invitation(
    payload: AcceptWorkspaceInvitationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMember:
    invitation = db.scalar(
        select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == hash_workspace_invite_token(payload.token))
    )
    now = datetime.now(timezone.utc)
    if not invitation or invitation.accepted_at is not None or invitation.revoked_at is not None or invitation.expires_at <= now:
        raise HTTPException(status_code=401, detail="Invalid or expired workspace invitation")
    if current_user.email.lower() != invitation.email.lower():
        raise HTTPException(status_code=403, detail="This invitation belongs to a different email address")

    existing = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == invitation.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if existing:
        existing.role = invitation.role
        membership = existing
    else:
        membership = WorkspaceMember(workspace_id=invitation.workspace_id, user_id=current_user.id, role=invitation.role)
        db.add(membership)
    invitation.accepted_at = func.now()
    log_action(
        db,
        action="workspace.invitation_accept",
        actor_id=current_user.id,
        workspace_id=invitation.workspace_id,
        metadata={"invitation_id": invitation.id, "role": invitation.role},
    )
    db.commit()
    db.refresh(membership)
    return membership


@router.get("/{workspace_id}/invitations", response_model=WorkspaceInvitationListResponse)
def list_invitations(
    workspace_id: int,
    include_closed: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceInvitationListResponse:
    require_workspace_admin(db, current_user, workspace_id)
    statement = select(WorkspaceInvitation).where(WorkspaceInvitation.workspace_id == workspace_id)
    if not include_closed:
        statement = statement.where(WorkspaceInvitation.accepted_at.is_(None), WorkspaceInvitation.revoked_at.is_(None))
    invitations = list(db.scalars(statement.order_by(WorkspaceInvitation.created_at.desc(), WorkspaceInvitation.id.desc())))
    now = datetime.now(timezone.utc)
    pending_count = sum(
        1
        for invitation in invitations
        if invitation.accepted_at is None and invitation.revoked_at is None and invitation.expires_at > now
    )
    return WorkspaceInvitationListResponse(invitations=invitations, pending_count=pending_count)


@router.post("/{workspace_id}/invitations/{invitation_id}/resend", response_model=WorkspaceInvitationResponse)
def resend_invitation(
    workspace_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceInvitation:
    require_workspace_admin(db, current_user, workspace_id)
    workspace = db.get(Workspace, workspace_id)
    invitation = db.get(WorkspaceInvitation, invitation_id)
    if not workspace or not invitation or invitation.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted_at is not None or invitation.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Invitation is already closed")

    raw_token = create_workspace_invite_token()
    invitation.token_hash = hash_workspace_invite_token(raw_token)
    invitation.expires_at = workspace_invite_expires_at()
    log_action(
        db,
        action="workspace.invitation_resend",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"invitation_id": invitation.id, "email": invitation.email, "role": invitation.role},
    )
    db.commit()
    db.refresh(invitation)
    send_workspace_invitation_email(invitation.email, workspace.name, invitation.role.value, current_user.email, raw_token)
    return invitation


@router.post("/{workspace_id}/invitations/{invitation_id}/revoke", response_model=WorkspaceInvitationResponse)
def revoke_invitation(
    workspace_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceInvitation:
    require_workspace_admin(db, current_user, workspace_id)
    invitation = db.get(WorkspaceInvitation, invitation_id)
    if not invitation or invitation.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Invitation has already been accepted")
    if invitation.revoked_at is None:
        invitation.revoked_at = func.now()
        log_action(
            db,
            action="workspace.invitation_revoke",
            actor_id=current_user.id,
            workspace_id=workspace_id,
            metadata={"invitation_id": invitation.id, "email": invitation.email},
        )
        db.commit()
        db.refresh(invitation)
    return invitation


@router.get("/{workspace_id}/audit", response_model=list[AuditLogResponse])
def list_audit_logs(
    workspace_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    require_workspace_member(db, current_user, workspace_id)
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
    )


@router.post("/{workspace_id}/ask", response_model=AskResponse)
def ask_workspace(
    workspace_id: int,
    payload: WorkspaceAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    require_workspace_member(db, current_user, workspace_id)
    response = answer_workspace_question(db, current_user.id, workspace_id, payload.question, payload.limit)
    log_action(
        db,
        action="workspace.ask",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"question": payload.question, "confidence": response.confidence, "prompt_version": response.prompt_version},
    )
    db.commit()
    return response


@router.post("/{workspace_id}/ask/stream")
def ask_workspace_stream(
    workspace_id: int,
    payload: WorkspaceAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_workspace_member(db, current_user, workspace_id)
    response = answer_workspace_question(db, current_user.id, workspace_id, payload.question, payload.limit)
    log_action(
        db,
        action="workspace.ask_stream",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"question": payload.question, "confidence": response.confidence, "prompt_version": response.prompt_version},
    )
    db.commit()

    def events():
        metadata = {
            "confidence": response.confidence,
            "prompt_version": response.prompt_version,
            "grounded": response.grounded,
        }
        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
        words = response.answer.split()
        for index in range(0, len(words), 18):
            yield f"event: token\ndata: {json.dumps({'text': ' '.join(words[index:index + 18]) + ' '})}\n\n"
        yield f"event: citations\ndata: {json.dumps([citation.model_dump() for citation in response.citations], default=str)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
