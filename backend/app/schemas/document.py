from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import DocumentAccessRole, DocumentReviewStatus, DocumentStatus, MessageRole


class DocumentResponse(BaseModel):
    id: int
    filename: str
    title: str | None
    collection_id: int | None
    content_type: str
    status: DocumentStatus
    summary: str | None
    key_fields: dict | None
    document_type: str | None
    document_type_confidence: int | None
    structured_fields: dict | None
    risk_flags: list[dict] | None
    tags: list[str]
    favorite: bool
    review_status: DocumentReviewStatus
    review_notes: str | None
    extraction_diagnostics: dict | None
    error_message: str | None
    page_count: int | None
    file_size_bytes: int | None
    retention_expires_at: datetime | None
    deleted_at: datetime | None
    deleted_by_id: int | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    extracted_text: str | None


class AskRequest(BaseModel):
    question: str


class UpdateDocumentOrganizationRequest(BaseModel):
    tags: list[str] | None = Field(default=None, max_length=25)
    favorite: bool | None = None
    collection_id: int | None = None


class UpdateDocumentReviewRequest(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    review_status: DocumentReviewStatus | None = None
    review_notes: str | None = Field(default=None, max_length=5000)


class BulkDocumentActionRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=100)
    tags_add: list[str] | None = Field(default=None, max_length=25)
    favorite: bool | None = None
    review_status: DocumentReviewStatus | None = None
    collection_id: int | None = None


class BulkDocumentActionResponse(BaseModel):
    updated: int
    documents: list[DocumentResponse]


class DocumentAnnotationRequest(BaseModel):
    page_number: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=5000)
    quote_text: str | None = Field(default=None, max_length=5000)
    color: str | None = Field(default=None, max_length=32)


class DocumentAnnotationResponse(BaseModel):
    id: int
    document_id: int
    user_id: int | None
    page_number: int
    quote_text: str | None
    note: str
    color: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentPermissionRequest(BaseModel):
    email: str
    role: DocumentAccessRole


class DocumentPermissionResponse(BaseModel):
    id: int
    document_id: int
    user_id: int
    role: DocumentAccessRole
    granted_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Citation(BaseModel):
    document_id: int | None = None
    filename: str | None = None
    chunk_index: int
    page_number: int | None
    text: str
    score: float | None = None
    validated: bool = False


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    prompt_version: str
    grounded: bool


class SearchRequest(BaseModel):
    query: str
    limit: int = 8
    workspace_id: int | None = None
    document_type: str | None = None
    status: DocumentStatus | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    risk_severity: str | None = None
    tag: str | None = None
    favorite: bool | None = None
    review_status: DocumentReviewStatus | None = None
    collection_id: int | None = None


class SearchResult(BaseModel):
    document_id: int
    filename: str
    chunk_index: int
    page_number: int | None
    text: str
    score: float
    vector_score: float
    keyword_score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class ChatMessageResponse(BaseModel):
    id: int
    role: MessageRole
    content: str
    citations: list[Citation] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceAskRequest(BaseModel):
    question: str
    limit: int = 8


class DocumentCompareRequest(BaseModel):
    other_document_id: int


class DocumentCompareSide(BaseModel):
    id: int
    filename: str
    document_type: str | None = None


class DocumentCompareResponse(BaseModel):
    left: DocumentCompareSide
    right: DocumentCompareSide
    similarity: float
    summary: dict
    field_changes: dict
    risk_changes: dict
    term_changes: dict
