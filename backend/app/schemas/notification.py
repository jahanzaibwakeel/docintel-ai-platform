from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: int | None
    document_id: int | None
    kind: str
    title: str
    message: str
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    unread_count: int
    notifications: list[NotificationResponse]
