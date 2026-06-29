from datetime import datetime

from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    users: int
    workspaces: int
    documents: int
    ready_documents: int
    failed_documents: int
    processing_documents: int
    uploaded_documents: int


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    workspace_count: int
    document_count: int
    created_at: datetime


class AdminWorkspaceResponse(BaseModel):
    id: int
    name: str
    member_count: int
    document_count: int
    created_at: datetime


class AdminDocumentResponse(BaseModel):
    id: int
    filename: str
    owner_email: str | None
    workspace_id: int | None
    status: str
    document_type: str | None
    error_message: str | None
    created_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
