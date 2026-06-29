from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import SearchRequest, SearchResponse
from app.services.search import semantic_search
from app.services.workspaces import require_workspace_member

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_documents(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    if payload.workspace_id is not None:
        require_workspace_member(db, current_user, payload.workspace_id)
    return semantic_search(
        db,
        current_user.id,
        payload.query,
        payload.limit,
        workspace_id=payload.workspace_id,
        document_type=payload.document_type,
        status=payload.status,
        created_from=payload.created_from,
        created_to=payload.created_to,
        risk_severity=payload.risk_severity,
        tag=payload.tag,
        favorite=payload.favorite,
        review_status=payload.review_status,
        collection_id=payload.collection_id,
    )
