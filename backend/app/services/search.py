import re

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentReviewStatus, DocumentStatus
from app.models.workspace import WorkspaceMember
from app.schemas.document import SearchResponse, SearchResult
from app.services.ai import embed_text


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9]{3,}", text.lower())}


def keyword_score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    text_tokens = _tokens(text)
    return len(query_tokens & text_tokens) / len(query_tokens)


def _apply_document_filters(
    statement,
    *,
    workspace_id: int | None = None,
    document_type: str | None = None,
    status: DocumentStatus | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    risk_severity: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
    review_status: DocumentReviewStatus | None = None,
    collection_id: int | None = None,
):
    if workspace_id is not None:
        statement = statement.where(Document.workspace_id == workspace_id)
    if document_type:
        statement = statement.where(Document.document_type == document_type)
    if status is not None:
        statement = statement.where(Document.status == status)
    if created_from is not None:
        statement = statement.where(Document.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(Document.created_at <= created_to)
    if risk_severity:
        statement = statement.where(Document.risk_flags.contains([{"severity": risk_severity}]))
    if tag:
        statement = statement.where(Document.tags.contains([tag.strip().lower()]))
    if favorite is not None:
        statement = statement.where(Document.favorite == favorite)
    if review_status is not None:
        statement = statement.where(Document.review_status == review_status)
    if collection_id is not None:
        statement = statement.where(Document.collection_id == collection_id)
    return statement


def semantic_search(
    db: Session,
    user_id: int,
    query: str,
    limit: int = 8,
    workspace_id: int | None = None,
    document_type: str | None = None,
    status: DocumentStatus | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    risk_severity: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
    review_status: DocumentReviewStatus | None = None,
    collection_id: int | None = None,
) -> SearchResponse:
    embedding = embed_text(query)
    distance = DocumentChunk.embedding.cosine_distance(embedding).label("distance")
    statement = (
        select(DocumentChunk, Document.filename, distance)
        .join(Document)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Document.workspace_id)
        .where(WorkspaceMember.user_id == user_id, Document.status == (status or DocumentStatus.ready))
        .order_by(distance)
        .limit(max(10, min(limit * 6, 60)))
    )
    statement = _apply_document_filters(
        statement,
        workspace_id=workspace_id,
        document_type=document_type,
        status=None,
        created_from=created_from,
        created_to=created_to,
        risk_severity=risk_severity,
        tag=tag,
        favorite=favorite,
        review_status=review_status,
        collection_id=collection_id,
    )
    rows = db.execute(statement).all()
    ranked = []
    for chunk, filename, distance_value in rows:
        vector_score = max(0.0, 1.0 - float(distance_value))
        lexical_score = keyword_score(query, chunk.text)
        final_score = (vector_score * 0.72) + (lexical_score * 0.28)
        ranked.append((final_score, vector_score, lexical_score, chunk, filename))
    ranked.sort(key=lambda item: item[0], reverse=True)

    return SearchResponse(
        results=[
            SearchResult(
                document_id=chunk.document_id,
                filename=filename,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                score=final_score,
                vector_score=vector_score,
                keyword_score=lexical_score,
            )
            for final_score, vector_score, lexical_score, chunk, filename in ranked[: max(1, min(limit, 25))]
        ]
    )
