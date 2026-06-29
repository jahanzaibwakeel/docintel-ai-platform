from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.workspace import WorkspaceRole


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class UpdateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.member


class UpdateMemberRoleRequest(BaseModel):
    role: WorkspaceRole


class AcceptWorkspaceInvitationRequest(BaseModel):
    token: str


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    user_email: EmailStr | None = None
    role: WorkspaceRole
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceInvitationResponse(BaseModel):
    id: int
    workspace_id: int
    email: EmailStr
    role: WorkspaceRole
    invited_by_id: int | None
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceInviteResponse(BaseModel):
    status: str
    member: WorkspaceMemberResponse | None = None
    invitation: WorkspaceInvitationResponse | None = None


class WorkspaceInvitationListResponse(BaseModel):
    invitations: list[WorkspaceInvitationResponse]
    pending_count: int


class AuditLogResponse(BaseModel):
    id: int
    workspace_id: int | None
    actor_id: int | None
    document_id: int | None
    action: str
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
