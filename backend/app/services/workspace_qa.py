from sqlalchemy.orm import Session

from app.schemas.document import AskResponse, Citation
from app.services.ai import chat
from app.services.qa import PROMPT_VERSION, confidence_from_citations, validate_citations
from app.services.search import semantic_search


def answer_workspace_question(db: Session, user_id: int, workspace_id: int, question: str, limit: int = 8) -> AskResponse:
    results = semantic_search(db, user_id=user_id, query=question, limit=limit, workspace_id=workspace_id).results
    citations = [
        Citation(
            document_id=result.document_id,
            filename=result.filename,
            chunk_index=result.chunk_index,
            page_number=result.page_number,
            text=result.text,
            score=result.score,
        )
        for result in results[:8]
    ]
    context = "\n\n".join(
        f"[{result.filename} | page {result.page_number or '-'} | chunk {result.chunk_index}] {result.text}"
        for result in results[:8]
    )
    answer = chat(f"Answer this cross-document question using only the context. Question: {question}", context)
    citations = validate_citations(answer, citations)
    confidence = confidence_from_citations(citations)
    return AskResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        prompt_version=PROMPT_VERSION,
        grounded=bool(citations) and any(citation.validated for citation in citations[:3]),
    )
