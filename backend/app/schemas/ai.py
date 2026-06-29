from pydantic import BaseModel


class AiProviderStatus(BaseModel):
    provider: str
    configured: bool
    healthy: bool | None
    model: str
    embedding_model: str
    embedding_dimensions: int
    max_context_chars: int
    request_timeout_seconds: int
    pii_redaction_enabled: bool
    external_ai_with_pii_allowed: bool
    detail: str
