from datetime import datetime

from pydantic import BaseModel, Field


class CollectionRequest(BaseModel):
    workspace_id: int
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class CollectionResponse(BaseModel):
    id: int
    workspace_id: int
    created_by_id: int | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
