from dataclasses import dataclass

from app.services.pdf import PageText


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_number: int | None


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_pages(pages: list[PageText], chunk_size: int, overlap: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page in pages:
        for chunk in chunk_text(page.text, chunk_size, overlap):
            chunks.append(TextChunk(text=chunk, page_number=page.page_number))
    if chunks:
        return chunks

    combined = "\n".join(page.text for page in pages)
    return [TextChunk(text=chunk, page_number=None) for chunk in chunk_text(combined, chunk_size, overlap)]
