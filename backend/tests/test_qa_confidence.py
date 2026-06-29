import unittest

from app.schemas.document import Citation
from app.services.qa import confidence_from_citations, validate_citations


class QaConfidenceTests(unittest.TestCase):
    def test_validation_and_confidence(self) -> None:
        citations = [
            Citation(chunk_index=1, page_number=2, text="The contract termination clause requires notice.", score=0.8)
        ]
        validated = validate_citations("The termination clause requires notice.", citations)
        self.assertTrue(validated[0].validated)
        self.assertGreater(confidence_from_citations(validated), 0.8)


if __name__ == "__main__":
    unittest.main()
