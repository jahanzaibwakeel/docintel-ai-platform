import unittest

from app.services.chunking import chunk_pages, chunk_text
from app.services.pdf import PageText


class ChunkingTests(unittest.TestCase):
    def test_chunk_text_overlaps(self) -> None:
        text = "abcdefghijklmnopqrstuvwxyz"
        chunks = chunk_text(text, chunk_size=10, overlap=3)
        self.assertEqual(chunks, ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"])

    def test_chunk_pages_preserves_page_numbers(self) -> None:
        pages = [
            PageText(page_number=1, text="alpha beta gamma", extraction_method="native", character_count=16),
            PageText(page_number=2, text="delta epsilon zeta", extraction_method="ocr", character_count=18),
        ]
        chunks = chunk_pages(pages, chunk_size=100, overlap=10)
        self.assertEqual([chunk.page_number for chunk in chunks], [1, 2])


if __name__ == "__main__":
    unittest.main()
