from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai import AiProviderStatus
from app.services.ai import provider_status

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status", response_model=AiProviderStatus)
def get_ai_status(
    health_check: bool = False,
    _current_user: User = Depends(get_current_user),
) -> AiProviderStatus:
    return AiProviderStatus(**provider_status(health_check=health_check))
