from sqlalchemy import delete
from sqlalchemy.sql import func

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.metrics import metrics
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.ai import analyze_document_intelligence, embed_text, extract_fields, summarize
from app.services.chunking import chunk_pages
from app.services.lifecycle import cleanup_expired_documents
from app.services.notifications import notify_document_failed, notify_document_ready
from app.services.pdf import extract_pdf_pages
from app.services.storage import get_storage
from app.services.workspaces import assert_workspace_page_quota
from app.worker.celery_app import celery_app


@celery_app.task(name="process_document")
def process_document(document_id: int) -> None:
    init_db()
    settings = get_settings()
    db = SessionLocal()
    try:
        metrics.increment("docintel_document_processing_jobs", status="started")
        document = db.get(Document, document_id)
        if not document or document.status == DocumentStatus.deleted:
            metrics.increment("docintel_document_processing_jobs", status="ignored")
            return

        with metrics.timer("docintel_document_processing_duration"):
            document.status = DocumentStatus.processing
            document.error_message = None
            document.processing_started_at = func.now()
            document.processing_completed_at = None
            db.commit()

            local_path = get_storage().open_local_path(document.storage_path)
            pages = extract_pdf_pages(local_path)
            if document.workspace_id is not None:
                assert_workspace_page_quota(db, document.workspace_id, document.id, len(pages))
            text = "\n".join(f"\n\n[Page {page.page_number}]\n{page.text}" for page in pages).strip()
            chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
            diagnostics = {
                "ocr_enabled": settings.enable_ocr,
                "page_count": len(pages),
                "ocr_page_count": sum(1 for page in pages if page.extraction_method == "ocr"),
                "native_page_count": sum(1 for page in pages if page.extraction_method == "native"),
                "failed_ocr_page_count": sum(1 for page in pages if page.extraction_method == "native_ocr_failed"),
                "pages": [
                    {
                        "page_number": page.page_number,
                        "method": page.extraction_method,
                        "character_count": page.character_count,
                        "error": page.error,
                    }
                    for page in pages
                ],
            }

            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            for index, chunk in enumerate(chunks):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        embedding=embed_text(chunk.text),
                    )
                )

            document.extracted_text = text
            document.page_count = len(pages)
            document.extraction_diagnostics = diagnostics
            document.summary = summarize(text)
            document.key_fields = extract_fields(text)
            intelligence = analyze_document_intelligence(text)
            document.document_type = intelligence.get("document_type")
            document.document_type_confidence = intelligence.get("document_type_confidence")
            document.structured_fields = intelligence.get("structured_fields")
            document.risk_flags = intelligence.get("risk_flags")
            document.status = DocumentStatus.ready
            document.processing_completed_at = func.now()
            notify_document_ready(db, document)
            db.commit()
        metrics.increment("docintel_document_processing_jobs", status="ready")
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document:
            document.status = DocumentStatus.failed
            document.error_message = str(exc)
            document.processing_completed_at = func.now()
            notify_document_failed(db, document)
            db.commit()
        metrics.increment("docintel_document_processing_jobs", status="failed")
        raise
    finally:
        db.close()


@celery_app.task(name="cleanup_expired_documents")
def cleanup_expired_documents_task(limit: int = 100) -> int:
    init_db()
    db = SessionLocal()
    try:
        count = cleanup_expired_documents(db, limit=limit)
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
