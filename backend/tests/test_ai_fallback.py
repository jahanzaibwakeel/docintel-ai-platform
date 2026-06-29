import unittest

from app.services.ai import analyze_document_intelligence


class AiFallbackTests(unittest.TestCase):
    def test_fallback_intelligence_detects_contract_risk(self) -> None:
        text = (
            "This Agreement shall terminate upon written notice. "
            "The parties agree to indemnification and governing law terms. "
            "Contact legal@example.com by 2026-01-01."
        )
        result = analyze_document_intelligence(text)
        self.assertIn(result["document_type"], {"contract", "general"})
        self.assertIsInstance(result["document_type_confidence"], int)
        self.assertTrue(result["risk_flags"])


if __name__ == "__main__":
    unittest.main()
