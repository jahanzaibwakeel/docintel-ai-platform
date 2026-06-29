from pathlib import Path
from typing import NamedTuple

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

from app.core.config import get_settings


class PageText(NamedTuple):
    page_number: int
    text: str
    extraction_method: str
    character_count: int
    error: str | None = None


def _ocr_page(path: str, page_number: int) -> tuple[str, str | None]:
    settings = get_settings()
    try:
        images = convert_from_path(path, dpi=settings.ocr_dpi, first_page=page_number, last_page=page_number)
        if not images:
            return "", "No page image was produced for OCR"
        return pytesseract.image_to_string(images[0]).strip(), None
    except Exception as exc:
        return "", str(exc)


def extract_pdf_pages(path: str, use_ocr: bool | None = None) -> list[PageText]:
    settings = get_settings()
    should_use_ocr = settings.enable_ocr if use_ocr is None else use_ocr
    reader = PdfReader(Path(path))
    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        native_text = (page.extract_text() or "").strip()
        method = "native"
        error = None
        text = native_text
        if should_use_ocr and len(native_text) < settings.ocr_min_chars_per_page:
            ocr_text, error = _ocr_page(path, index)
            if ocr_text:
                text = ocr_text
                method = "ocr"
            elif error:
                method = "native_ocr_failed"
        pages.append(
            PageText(
                page_number=index,
                text=text,
                extraction_method=method,
                character_count=len(text),
                error=error,
            )
        )
    return pages


def extract_pdf_text(path: str) -> tuple[str, int]:
    pages = extract_pdf_pages(path)
    text = "\n".join(f"\n\n[Page {page.page_number}]\n{page.text}" for page in pages).strip()
    return text, len(pages)
