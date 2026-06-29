import re

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "api_key": re.compile(r"\b(?:sk|pk|api|key)[_-]?[A-Za-z0-9]{20,}\b", re.I),
}


def detect_pii(text: str) -> dict[str, int]:
    return {label: len(pattern.findall(text)) for label, pattern in PII_PATTERNS.items() if pattern.search(text)}


def redact_pii(text: str) -> str:
    redacted = text
    for label, pattern in PII_PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted

