from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.schemas.document import AskResponse, Citation
from app.services.ai import chat, embed_text
from app.services.search import keyword_score

PROMPT_VERSION = "rag-v2-grounded-citations"


def validate_citations(answer: str, citations: list[Citation]) -> list[Citation]:
    answer_tokens = {token.lower() for token in answer.split() if len(token) > 4}
    validated = []
    for citation in citations:
        citation_tokens = {token.lower() for token in citation.text.split() if len(token) > 4}
        overlap = bool(answer_tokens & citation_tokens) or (citation.score or 0) >= 0.55
        validated.append(citation.model_copy(update={"validated": overlap}))
    return validated


def confidence_from_citations(citations: list[Citation]) -> float:
    if not citations:
        return 0.0
    average = sum(citation.score or 0 for citation in citations) / len(citations)
    validated_bonus = sum(1 for citation in citations if citation.validated) / len(citations) * 0.15
    return round(min(1.0, average + validated_bonus), 3)


def answer_question(db: Session, document: Document, question: str) -> AskResponse:
    embedding = embed_text(question)
    distance = DocumentChunk.embedding.cosine_distance(embedding).label("distance")
    chunks = db.execute(
        select(DocumentChunk, distance)
        .where(DocumentChunk.document_id == document.id)
        .order_by(distance)
        .limit(20)
    ).all()
    if not chunks:
        context = (document.extracted_text or "")[:8000]
        citations = []
    else:
        ranked = []
        for chunk, distance_value in chunks:
            vector_score = max(0.0, 1.0 - float(distance_value))
            lexical_score = keyword_score(question, chunk.text)
            score = (vector_score * 0.72) + (lexical_score * 0.28)
            ranked.append((score, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        top_chunks = ranked[:5]
        context = "\n\n".join(f"[Chunk {chunk.chunk_index}] {chunk.text}" for _score, chunk in top_chunks)
        citations = [
            Citation(
                document_id=document.id,
                filename=document.filename,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                score=score,
            )
            for score, chunk in top_chunks
        ]
    answer = chat(f"Answer this question using the context and cite only supported facts. Question: {question}", context)
    citations = validate_citations(answer, citations)
    confidence = confidence_from_citations(citations)
    return AskResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        prompt_version=PROMPT_VERSION,
        grounded=bool(citations) and all(citation.validated for citation in citations[:2]),
    )
