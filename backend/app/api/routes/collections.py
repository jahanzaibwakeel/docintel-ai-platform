from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.document import DocumentCollection
from app.models.user import User
from app.schemas.collection import CollectionRequest, CollectionResponse
from app.services.audit import log_action
from app.services.workspaces import require_workspace_member, require_workspace_writer

router = APIRouter(prefix="/collections", tags=["collections"])


def get_collection(db: Session, collection_id: int) -> DocumentCollection:
    collection = db.get(DocumentCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.get("", response_model=list[CollectionResponse])
def list_collections(
    workspace_id: int = Query(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentCollection]:
    require_workspace_member(db, current_user, workspace_id)
    return list(
        db.scalars(
            select(DocumentCollection)
            .where(DocumentCollection.workspace_id == workspace_id)
            .order_by(DocumentCollection.name.asc(), DocumentCollection.id.asc())
        )
    )


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentCollection:
    require_workspace_writer(db, current_user, payload.workspace_id)
    collection = DocumentCollection(
        workspace_id=payload.workspace_id,
        created_by_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(collection)
    log_action(db, action="collection.create", actor_id=current_user.id, workspace_id=payload.workspace_id, metadata={"name": collection.name})
    db.commit()
    db.refresh(collection)
    return collection


@router.patch("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int,
    payload: CollectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentCollection:
    collection = get_collection(db, collection_id)
    if collection.workspace_id != payload.workspace_id:
        raise HTTPException(status_code=400, detail="Collection workspace cannot be changed")
    require_workspace_writer(db, current_user, collection.workspace_id)
    collection.name = payload.name.strip()
    collection.description = payload.description.strip() if payload.description else None
    log_action(db, action="collection.update", actor_id=current_user.id, workspace_id=collection.workspace_id, metadata={"collection_id": collection.id, "name": collection.name})
    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    collection = get_collection(db, collection_id)
    require_workspace_writer(db, current_user, collection.workspace_id)
    workspace_id = collection.workspace_id
    db.delete(collection)
    log_action(db, action="collection.delete", actor_id=current_user.id, workspace_id=workspace_id, metadata={"collection_id": collection_id})
    db.commit()
