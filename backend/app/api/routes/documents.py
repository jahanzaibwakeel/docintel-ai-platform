from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document, DocumentAnnotation, DocumentCollection, DocumentMessage, DocumentReviewStatus, DocumentStatus, MessageRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.document import (
    AskRequest,
    AskResponse,
    BulkDocumentActionRequest,
    BulkDocumentActionResponse,
    ChatMessageResponse,
    DocumentCompareRequest,
    DocumentCompareResponse,
    DocumentAnnotationRequest,
    DocumentAnnotationResponse,
    DocumentDetailResponse,
    DocumentResponse,
    UpdateDocumentOrganizationRequest,
    UpdateDocumentReviewRequest,
)
from app.services.audit import log_action
from app.services.compare import compare_documents
from app.services.export import document_export_markdown, document_export_payload
from app.services.lifecycle import apply_default_retention, delete_document
from app.services.qa import answer_question
from app.services.storage import get_storage
from app.services.workspaces import get_default_workspace, require_workspace_member, require_workspace_writer
from app.worker.tasks import process_document

router = APIRouter(prefix="/documents", tags=["documents"])


def normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = tag.strip().lower()
        if not value or value in seen:
            continue
        if len(value) > 40:
            raise HTTPException(status_code=400, detail="Tags must be 40 characters or fewer")
        seen.add(value)
        normalized.append(value)
    return normalized[:25]


def get_owned_document(document_id: int, user: User, db: Session) -> Document:
    document = db.scalar(
        select(Document)
        .options(selectinload(Document.chunks), selectinload(Document.messages))
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Document.workspace_id)
        .where(Document.id == document_id, WorkspaceMember.user_id == user.id)
    )
    if not document or document.status == DocumentStatus.deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def validate_collection(db: Session, user: User, collection_id: int | None, workspace_id: int | None) -> DocumentCollection | None:
    if collection_id is None:
        return None
    collection = db.get(DocumentCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    require_workspace_member(db, user, collection.workspace_id)
    if workspace_id is not None and collection.workspace_id != workspace_id:
        raise HTTPException(status_code=400, detail="Collection belongs to a different workspace")
    return collection


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    workspace_id: int | None = Query(default=None),
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    document_type: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    risk_severity: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    review_status: DocumentReviewStatus | None = Query(default=None),
    collection_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Document]:
    statement = select(Document).where(Document.status != DocumentStatus.deleted)
    if workspace_id is not None:
        require_workspace_member(db, current_user, workspace_id)
        statement = statement.where(Document.workspace_id == workspace_id)
    else:
        statement = statement.join(WorkspaceMember, WorkspaceMember.workspace_id == Document.workspace_id).where(WorkspaceMember.user_id == current_user.id)
    if status_filter is not None:
        statement = statement.where(Document.status == status_filter)
    if document_type:
        statement = statement.where(Document.document_type == document_type)
    if created_from:
        statement = statement.where(Document.created_at >= created_from)
    if created_to:
        statement = statement.where(Document.created_at <= created_to)
    if risk_severity:
        statement = statement.where(Document.risk_flags.contains([{"severity": risk_severity}]))
    if tag:
        statement = statement.where(Document.tags.contains([tag.strip().lower()]))
    if favorite is not None:
        statement = statement.where(Document.favorite == favorite)
    if review_status:
        statement = statement.where(Document.review_status == review_status)
    if collection_id is not None:
        statement = statement.where(Document.collection_id == collection_id)
    return list(db.scalars(statement.order_by(Document.created_at.desc())))


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    workspace_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    settings = get_settings()
    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    max_size = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail=f"PDF exceeds the {settings.max_upload_mb} MB upload limit")
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")

    workspace = get_default_workspace(db, current_user) if workspace_id is None else None
    if workspace_id is not None:
        require_workspace_writer(db, current_user, workspace_id)
        workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    storage_path = get_storage().save_pdf(workspace.id, contents)

    document = Document(
        owner_id=current_user.id,
        workspace_id=workspace.id,
        filename=file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        content_type=file.content_type or "application/pdf",
        storage_path=str(storage_path),
        file_size_bytes=len(contents),
        status=DocumentStatus.uploaded,
    )
    apply_default_retention(document)
    db.add(document)
    log_action(
        db,
        action="document.upload",
        actor_id=current_user.id,
        workspace_id=workspace.id,
        metadata={"filename": document.filename, "bytes": len(contents), "storage_provider": settings.storage_provider},
    )
    db.commit()
    db.refresh(document)
    process_document.delay(document.id)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_route(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document = get_owned_document(document_id, current_user, db)
    require_workspace_writer(db, current_user, document.workspace_id)
    delete_document(db, document, actor_id=current_user.id, reason="user_requested")
    db.commit()


@router.post("/bulk", response_model=BulkDocumentActionResponse)
def bulk_document_action(
    payload: BulkDocumentActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkDocumentActionResponse:
    document_ids = list(dict.fromkeys(payload.document_ids))
    documents = list(
        db.scalars(
            select(Document)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Document.workspace_id)
            .where(Document.id.in_(document_ids), WorkspaceMember.user_id == current_user.id, Document.status != DocumentStatus.deleted)
        )
    )
    if len(documents) != len(document_ids):
        raise HTTPException(status_code=404, detail="One or more documents were not found")

    target_collection = validate_collection(db, current_user, payload.collection_id, None) if payload.collection_id is not None else None
    tags_to_add = normalize_tags(payload.tags_add or [])
    for document in documents:
        require_workspace_writer(db, current_user, document.workspace_id)
        if target_collection and target_collection.workspace_id != document.workspace_id:
            raise HTTPException(status_code=400, detail="Collection belongs to a different workspace")
        if tags_to_add:
            document.tags = normalize_tags([*(document.tags or []), *tags_to_add])
        if payload.favorite is not None:
            document.favorite = payload.favorite
        if payload.review_status is not None:
            document.review_status = payload.review_status
        if target_collection is not None:
            document.collection_id = target_collection.id
    log_action(
        db,
        action="document.bulk_update",
        actor_id=current_user.id,
        workspace_id=documents[0].workspace_id if len({document.workspace_id for document in documents}) == 1 else None,
        metadata={"document_ids": document_ids, "updated": len(documents)},
    )
    db.commit()
    for document in documents:
        db.refresh(document)
    return BulkDocumentActionResponse(updated=len(documents), documents=documents)


@router.patch("/{document_id}/organization", response_model=DocumentResponse)
def update_document_organization(
    document_id: int,
    payload: UpdateDocumentOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    document = get_owned_document(document_id, current_user, db)
    require_workspace_writer(db, current_user, document.workspace_id)
    if payload.tags is not None:
        document.tags = normalize_tags(payload.tags)
    if payload.favorite is not None:
        document.favorite = payload.favorite
    if payload.collection_id is not None:
        collection = validate_collection(db, current_user, payload.collection_id, document.workspace_id)
        document.collection_id = collection.id if collection else None
    log_action(
        db,
        action="document.organization_update",
        actor_id=current_user.id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        metadata={"tags": document.tags, "favorite": document.favorite, "collection_id": document.collection_id},
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}/annotations", response_model=list[DocumentAnnotationResponse])
def list_document_annotations(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentAnnotation]:
    document = get_owned_document(document_id, current_user, db)
    return list(
        db.scalars(
            select(DocumentAnnotation)
            .where(DocumentAnnotation.document_id == document.id)
            .order_by(DocumentAnnotation.page_number.asc(), DocumentAnnotation.created_at.asc(), DocumentAnnotation.id.asc())
        )
    )


@router.post("/{document_id}/annotations", response_model=DocumentAnnotationResponse, status_code=status.HTTP_201_CREATED)
def create_document_annotation(
    document_id: int,
    payload: DocumentAnnotationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentAnnotation:
    document = get_owned_document(document_id, current_user, db)
    require_workspace_writer(db, current_user, document.workspace_id)
    annotation = DocumentAnnotation(
        document_id=document.id,
        user_id=current_user.id,
        page_number=payload.page_number,
        quote_text=payload.quote_text.strip() if payload.quote_text else None,
        note=payload.note.strip(),
        color=payload.color.strip() if payload.color else None,
    )
    db.add(annotation)
    log_action(db, action="document.annotation_create", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id, metadata={"page_number": annotation.page_number})
    db.commit()
    db.refresh(annotation)
    return annotation


@router.delete("/{document_id}/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_annotation(
    document_id: int,
    annotation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document = get_owned_document(document_id, current_user, db)
    require_workspace_writer(db, current_user, document.workspace_id)
    annotation = db.get(DocumentAnnotation, annotation_id)
    if not annotation or annotation.document_id != document.id:
        raise HTTPException(status_code=404, detail="Annotation not found")
    db.delete(annotation)
    log_action(db, action="document.annotation_delete", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id, metadata={"annotation_id": annotation_id})
    db.commit()


@router.patch("/{document_id}/review", response_model=DocumentResponse)
def update_document_review(
    document_id: int,
    payload: UpdateDocumentReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    document = get_owned_document(document_id, current_user, db)
    require_workspace_writer(db, current_user, document.workspace_id)
    if payload.title is not None:
        document.title = payload.title.strip() or None
    if payload.review_status is not None:
        document.review_status = payload.review_status
    if payload.review_notes is not None:
        document.review_notes = payload.review_notes.strip() or None
    log_action(
        db,
        action="document.review_update",
        actor_id=current_user.id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        metadata={"title": document.title, "review_status": document.review_status},
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    document = get_owned_document(document_id, current_user, db)
    log_action(db, action="document.view", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id)
    db.commit()
    return document


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    document = get_owned_document(document_id, current_user, db)
    log_action(db, action="document.download", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id)
    db.commit()
    try:
        return get_storage().response(document.storage_path, document.filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Stored PDF file was not found")


@router.get("/{document_id}/export")
def export_document(
    document_id: int,
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    document = get_owned_document(document_id, current_user, db)
    log_action(db, action="document.export", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id, metadata={"format": format})
    db.commit()
    safe_name = document.filename.rsplit(".", 1)[0].replace('"', "").replace("\\", "-").replace("/", "-")
    if format == "markdown":
        return Response(
            document_export_markdown(document),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.md"'},
        )
    return JSONResponse(
        document_export_payload(document),
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'},
    )


@router.post("/{document_id}/compare", response_model=DocumentCompareResponse)
def compare_document_route(
    document_id: int,
    payload: DocumentCompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    document = get_owned_document(document_id, current_user, db)
    other = get_owned_document(payload.other_document_id, current_user, db)
    if document.workspace_id != other.workspace_id:
        raise HTTPException(status_code=400, detail="Documents must belong to the same workspace")
    result = compare_documents(document, other)
    log_action(
        db,
        action="document.compare",
        actor_id=current_user.id,
        workspace_id=document.workspace_id,
        document_id=document.id,
        metadata={"other_document_id": other.id, "similarity": result["similarity"]},
    )
    db.commit()
    return result


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    document = get_owned_document(document_id, current_user, db)
    require_workspace_writer(db, current_user, document.workspace_id)
    document.status = DocumentStatus.uploaded
    document.error_message = None
    document.extraction_diagnostics = None
    document.processing_started_at = None
    document.processing_completed_at = None
    log_action(db, action="document.reprocess", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id)
    db.commit()
    db.refresh(document)
    process_document.delay(document.id)
    return document


@router.get("/{document_id}/messages", response_model=list[ChatMessageResponse])
def list_document_messages(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentMessage]:
    document = get_owned_document(document_id, current_user, db)
    return list(
        db.scalars(
            select(DocumentMessage)
            .where(DocumentMessage.document_id == document.id)
            .order_by(DocumentMessage.created_at.asc(), DocumentMessage.id.asc())
        )
    )


@router.delete("/{document_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
def clear_document_messages(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document = get_owned_document(document_id, current_user, db)
    log_action(db, action="chat.clear", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id)
    for message in document.messages:
        db.delete(message)
    db.commit()


@router.post("/{document_id}/ask", response_model=AskResponse)
def ask_document(
    document_id: int,
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    document = get_owned_document(document_id, current_user, db)
    if document.status != DocumentStatus.ready:
        raise HTTPException(status_code=409, detail="Document is not ready for questions yet")
    response = answer_question(db, document, payload.question)
    log_action(db, action="document.ask", actor_id=current_user.id, workspace_id=document.workspace_id, document_id=document.id)
    db.add(DocumentMessage(document_id=document.id, role=MessageRole.user, content=payload.question, citations=None))
    db.add(
        DocumentMessage(
            document_id=document.id,
            role=MessageRole.assistant,
            content=response.answer,
            citations=[citation.model_dump() for citation in response.citations],
        )
    )
    db.commit()
    return response
