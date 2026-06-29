import hashlib
import json
import re
from collections import Counter
from math import sqrt

import httpx

from app.core.config import get_settings
from app.services.pii import detect_pii, redact_pii


def _external_ai_text(text: str) -> str:
    settings = get_settings()
    if settings.ai_provider not in {"openai", "ollama"}:
        return text
    pii = detect_pii(text)
    if not pii:
        return text
    if settings.redact_pii_for_external_ai:
        return redact_pii(text)
    if not settings.allow_external_ai_with_pii:
        raise ValueError("PII detected. Enable REDACT_PII_FOR_EXTERNAL_AI or ALLOW_EXTERNAL_AI_WITH_PII to use external AI.")
    return text


def _fallback_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1 if digest[4] % 2 == 0 else -1
        vector[index] += sign
    norm = sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _fallback_summary(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [sentence for sentence in sentences if len(sentence) > 30]
    return " ".join(sentences[:5])[:1800] or text[:1000] or "No extractable text was found."


def _fallback_fields(text: str) -> dict:
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)))
    phones = sorted(set(re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", text)))
    amounts = sorted(set(re.findall(r"(?:USD|EUR|GBP|PKR|\$)\s?[\d,]+(?:\.\d{2})?", text, flags=re.I)))
    dates = sorted(set(re.findall(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", text)))
    capitalized = re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", text)
    common = [value for value, _count in Counter(capitalized).most_common(12)]
    clauses = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if "shall" in sentence.lower() or "must" in sentence.lower()]
    return {
        "names_or_organizations": common,
        "dates": dates[:20],
        "amounts": amounts[:20],
        "emails": emails[:20],
        "phone_numbers": phones[:20],
        "important_clauses": clauses[:8],
    }


def _classification_scores(text: str) -> dict[str, int]:
    lowered = text.lower()
    signals = {
        "contract": ["agreement", "party", "term", "termination", "governing law", "indemnify", "shall"],
        "invoice": ["invoice", "amount due", "subtotal", "tax", "payment terms", "bill to", "invoice number"],
        "resume": ["experience", "education", "skills", "employment", "resume", "curriculum vitae"],
        "policy": ["policy", "procedure", "compliance", "scope", "responsibility", "effective date"],
        "financial_report": ["balance sheet", "income statement", "cash flow", "revenue", "assets", "liabilities"],
        "research_report": ["abstract", "methodology", "findings", "references", "conclusion"],
    }
    return {doc_type: sum(1 for signal in doc_signals if signal in lowered) for doc_type, doc_signals in signals.items()}


def _fallback_structured_intelligence(text: str) -> dict:
    fields = _fallback_fields(text)
    scores = _classification_scores(text)
    document_type, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        document_type = "general"
    confidence = min(95, 35 + score * 12)
    structured_fields = {
        key: [{"value": value, "confidence": 70, "source": "pattern"} for value in values]
        for key, values in fields.items()
        if isinstance(values, list)
    }
    risk_patterns = [
        ("high", "termination", r"[^.?!]*(?:terminate|termination)[^.?!]*[.?!]"),
        ("high", "indemnification", r"[^.?!]*(?:indemnify|indemnification|hold harmless)[^.?!]*[.?!]"),
        ("medium", "late payment", r"[^.?!]*(?:late fee|penalty|interest)[^.?!]*[.?!]"),
        ("medium", "confidentiality", r"[^.?!]*(?:confidential|non-disclosure|nondisclosure)[^.?!]*[.?!]"),
        ("medium", "governing law", r"[^.?!]*(?:governing law|jurisdiction|venue)[^.?!]*[.?!]"),
        ("low", "renewal", r"[^.?!]*(?:renewal|auto-renew|automatically renew)[^.?!]*[.?!]"),
    ]
    risk_flags = []
    for severity, label, pattern in risk_patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            risk_flags.append(
                {
                    "label": label,
                    "severity": severity,
                    "confidence": 72,
                    "evidence": match.group(0).strip()[:500],
                }
            )
    return {
        "document_type": document_type,
        "document_type_confidence": confidence,
        "structured_fields": structured_fields,
        "risk_flags": risk_flags,
    }


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        text = _external_ai_text(text)
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.openai_embedding_model, "input": text, "dimensions": settings.embedding_dimensions},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    if settings.ai_provider == "ollama":
        text = _external_ai_text(text)
        response = httpx.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embedding_model, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
        embedding = response.json()["embedding"]
        if len(embedding) >= settings.embedding_dimensions:
            return embedding[: settings.embedding_dimensions]
        return embedding + [0.0] * (settings.embedding_dimensions - len(embedding))
    return _fallback_embedding(text, settings.embedding_dimensions)


def chat(prompt: str, context: str) -> str:
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        context = _external_ai_text(context)
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": [
                    {"role": "system", "content": "You are a careful document intelligence assistant. Answer only from the supplied context."},
                    {"role": "user", "content": f"Context:\n{context}\n\nTask:\n{prompt}"},
                ],
                "temperature": 0.2,
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    if settings.ai_provider == "ollama":
        context = _external_ai_text(context)
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": f"Context:\n{context}\n\nTask:\n{prompt}", "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    if "JSON" in prompt:
        return json.dumps(_fallback_fields(context), indent=2)
    if "question" in prompt.lower():
        return _fallback_summary(context)
    return _fallback_summary(context)


def summarize(text: str) -> str:
    return chat("Create a concise executive summary with key risks, obligations, dates, and decisions.", text[:14000])


def extract_fields(text: str) -> dict:
    prompt = (
        "Extract key fields as strict JSON with keys: names, dates, organizations, amounts, emails, "
        "phone_numbers, important_clauses. Use arrays of strings. Return JSON only."
    )
    raw = chat(prompt, text[:16000])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_fields(text)


def analyze_document_intelligence(text: str) -> dict:
    prompt = (
        "Return strict JSON for document intelligence with keys: document_type, "
        "document_type_confidence as an integer 0-100, structured_fields as an object where each key maps "
        "to an array of {value, confidence, source}, and risk_flags as an array of "
        "{label, severity, confidence, evidence}. Use severity low, medium, or high. Return JSON only."
    )
    raw = chat(prompt, text[:18000])
    try:
        parsed = json.loads(raw)
        fallback = _fallback_structured_intelligence(text)
        return {
            "document_type": parsed.get("document_type") or fallback["document_type"],
            "document_type_confidence": parsed.get("document_type_confidence") or fallback["document_type_confidence"],
            "structured_fields": parsed.get("structured_fields") or fallback["structured_fields"],
            "risk_flags": parsed.get("risk_flags") or fallback["risk_flags"],
        }
    except (json.JSONDecodeError, AttributeError):
        return _fallback_structured_intelligence(text)
