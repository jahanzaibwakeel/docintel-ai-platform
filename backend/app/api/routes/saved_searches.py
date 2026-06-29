from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.saved_search import SavedSearch
from app.models.user import User
from app.schemas.saved_search import SavedSearchRequest, SavedSearchResponse
from app.services.audit import log_action
from app.services.workspaces import require_workspace_member

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


def get_owned_saved_search(db: Session, user: User, saved_search_id: int) -> SavedSearch:
    saved_search = db.get(SavedSearch, saved_search_id)
    if not saved_search or saved_search.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return saved_search


def validate_workspace_access(db: Session, user: User, workspace_id: int | None) -> None:
    if workspace_id is not None:
        require_workspace_member(db, user, workspace_id)


@router.get("", response_model=list[SavedSearchResponse])
def list_saved_searches(
    workspace_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedSearch]:
    statement = select(SavedSearch).where(SavedSearch.user_id == current_user.id)
    if workspace_id is not None:
        require_workspace_member(db, current_user, workspace_id)
        statement = statement.where(SavedSearch.workspace_id == workspace_id)
    return list(db.scalars(statement.order_by(SavedSearch.updated_at.desc(), SavedSearch.id.desc())))


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    payload: SavedSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearch:
    validate_workspace_access(db, current_user, payload.workspace_id)
    saved_search = SavedSearch(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        name=payload.name.strip(),
        query=payload.query.strip(),
        filters=payload.filters,
    )
    db.add(saved_search)
    log_action(
        db,
        action="saved_search.create",
        actor_id=current_user.id,
        workspace_id=payload.workspace_id,
        metadata={"name": saved_search.name},
    )
    db.commit()
    db.refresh(saved_search)
    return saved_search


@router.patch("/{saved_search_id}", response_model=SavedSearchResponse)
def update_saved_search(
    saved_search_id: int,
    payload: SavedSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearch:
    saved_search = get_owned_saved_search(db, current_user, saved_search_id)
    validate_workspace_access(db, current_user, payload.workspace_id)
    saved_search.workspace_id = payload.workspace_id
    saved_search.name = payload.name.strip()
    saved_search.query = payload.query.strip()
    saved_search.filters = payload.filters
    log_action(
        db,
        action="saved_search.update",
        actor_id=current_user.id,
        workspace_id=payload.workspace_id,
        metadata={"saved_search_id": saved_search.id, "name": saved_search.name},
    )
    db.commit()
    db.refresh(saved_search)
    return saved_search


@router.delete("/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(
    saved_search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    saved_search = get_owned_saved_search(db, current_user, saved_search_id)
    workspace_id = saved_search.workspace_id
    db.delete(saved_search)
    log_action(
        db,
        action="saved_search.delete",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        metadata={"saved_search_id": saved_search_id},
    )
    db.commit()
