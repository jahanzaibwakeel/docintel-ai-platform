from datetime import datetime
from typing import Any

from app.models.document import Document


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def document_export_payload(document: Document) -> dict[str, Any]:
    return {
        "id": document.id,
        "filename": document.filename,
        "title": document.title,
        "collection_id": document.collection_id,
        "status": document.status,
        "review_status": document.review_status,
        "review_notes": document.review_notes,
        "tags": document.tags,
        "favorite": document.favorite,
        "document_type": document.document_type,
        "document_type_confidence": document.document_type_confidence,
        "summary": document.summary,
        "key_fields": document.key_fields,
        "structured_fields": document.structured_fields,
        "risk_flags": document.risk_flags,
        "page_count": document.page_count,
        "file_size_bytes": document.file_size_bytes,
        "extraction_diagnostics": document.extraction_diagnostics,
        "processing_started_at": _iso(document.processing_started_at),
        "processing_completed_at": _iso(document.processing_completed_at),
        "created_at": _iso(document.created_at),
        "updated_at": _iso(document.updated_at),
        "extracted_text": document.extracted_text,
    }


def _lines_for_values(values: Any) -> list[str]:
    if not values:
        return ["- None found"]
    if isinstance(values, list):
        return [f"- {value}" for value in values]
    return [f"- {values}"]


def document_export_markdown(document: Document) -> str:
    payload = document_export_payload(document)
    lines = [
        f"# {document.title or document.filename}",
        "",
        "## Metadata",
        f"- Filename: {document.filename}",
        f"- Status: {document.status}",
        f"- Review status: {document.review_status}",
        f"- Favorite: {'yes' if document.favorite else 'no'}",
        f"- Tags: {', '.join(document.tags) if document.tags else '-'}",
        f"- Document type: {document.document_type or 'Unknown'}",
        f"- Type confidence: {document.document_type_confidence if document.document_type_confidence is not None else '-'}",
        f"- Pages: {document.page_count if document.page_count is not None else '-'}",
        f"- File size bytes: {document.file_size_bytes if document.file_size_bytes is not None else '-'}",
        f"- Created: {payload['created_at'] or '-'}",
        f"- Processed: {payload['processing_completed_at'] or '-'}",
        "",
        "## Summary",
        document.summary or "No summary available.",
        "",
        "## Key Fields",
    ]

    key_fields = document.key_fields or {}
    if key_fields:
        for key, values in key_fields.items():
            lines.append(f"### {key.replace('_', ' ').title()}")
            lines.extend(_lines_for_values(values))
    else:
        lines.append("- None found")

    lines.extend(["", "## Structured Fields"])
    structured_fields = document.structured_fields or {}
    if structured_fields:
        for group, values in structured_fields.items():
            lines.append(f"### {group.replace('_', ' ').title()}")
            for value in values:
                if isinstance(value, dict):
                    confidence = value.get("confidence")
                    suffix = f" ({confidence}%)" if confidence is not None else ""
                    lines.append(f"- {value.get('value', '')}{suffix}")
                else:
                    lines.append(f"- {value}")
    else:
        lines.append("- None found")

    lines.extend(["", "## Risk Flags"])
    risk_flags = document.risk_flags or []
    if risk_flags:
        for risk in risk_flags:
            label = risk.get("label", "Risk") if isinstance(risk, dict) else "Risk"
            severity = risk.get("severity", "unknown") if isinstance(risk, dict) else "unknown"
            evidence = risk.get("evidence", "") if isinstance(risk, dict) else str(risk)
            lines.append(f"- {label} [{severity}]: {evidence}")
    else:
        lines.append("- None found")

    lines.extend(["", "## Review Notes", document.review_notes or "No review notes."])

    lines.extend(["", "## Extracted Text", document.extracted_text or "No extracted text available."])
    return "\n".join(lines).strip() + "\n"
