from datetime import datetime

from pydantic import BaseModel, Field


class SavedSearchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    query: str = Field(min_length=1, max_length=2000)
    workspace_id: int | None = None
    filters: dict = Field(default_factory=dict)


class SavedSearchResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: int | None
    name: str
    query: str
    filters: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
