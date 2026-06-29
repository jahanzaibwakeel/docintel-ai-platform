import re
from difflib import SequenceMatcher
from typing import Any

from app.models.document import Document


def _normalize_values(values: Any) -> set[str]:
    if not values:
        return set()
    if isinstance(values, list):
        normalized: set[str] = set()
        for value in values:
            if isinstance(value, dict):
                item = value.get("value")
            else:
                item = value
            if item is not None:
                normalized.add(str(item).strip())
        return {value for value in normalized if value}
    return {str(values).strip()}


def _risk_labels(risks: list | None) -> set[str]:
    labels: set[str] = set()
    for risk in risks or []:
        if isinstance(risk, dict):
            label = risk.get("label")
            if label:
                labels.add(str(label))
        else:
            labels.add(str(risk))
    return labels


def _terms(text: str | None) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text or "")
    stopwords = {"the", "and", "for", "with", "that", "this", "from", "shall", "will", "are", "was"}
    return {word.lower() for word in words if word.lower() not in stopwords}


def compare_documents(left: Document, right: Document) -> dict[str, Any]:
    left_text = left.extracted_text or left.summary or ""
    right_text = right.extracted_text or right.summary or ""
    left_terms = _terms(left_text)
    right_terms = _terms(right_text)
    common_terms = sorted(left_terms & right_terms)
    left_only_terms = sorted(left_terms - right_terms)
    right_only_terms = sorted(right_terms - left_terms)

    all_field_keys = sorted(set((left.key_fields or {}).keys()) | set((right.key_fields or {}).keys()))
    field_changes: dict[str, dict[str, list[str]]] = {}
    for key in all_field_keys:
        left_values = _normalize_values((left.key_fields or {}).get(key))
        right_values = _normalize_values((right.key_fields or {}).get(key))
        if left_values != right_values:
            field_changes[key] = {
                "only_in_left": sorted(left_values - right_values),
                "only_in_right": sorted(right_values - left_values),
                "shared": sorted(left_values & right_values),
            }

    left_risks = _risk_labels(left.risk_flags)
    right_risks = _risk_labels(right.risk_flags)
    similarity = SequenceMatcher(None, left_text, right_text).ratio() if left_text or right_text else 1.0

    return {
        "left": {"id": left.id, "filename": left.filename, "document_type": left.document_type},
        "right": {"id": right.id, "filename": right.filename, "document_type": right.document_type},
        "similarity": round(similarity, 4),
        "summary": {
            "left": left.summary,
            "right": right.summary,
            "changed": (left.summary or "") != (right.summary or ""),
        },
        "field_changes": field_changes,
        "risk_changes": {
            "only_in_left": sorted(left_risks - right_risks),
            "only_in_right": sorted(right_risks - left_risks),
            "shared": sorted(left_risks & right_risks),
        },
        "term_changes": {
            "common": common_terms[:25],
            "only_in_left": left_only_terms[:25],
            "only_in_right": right_only_terms[:25],
        },
    }
