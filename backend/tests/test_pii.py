import unittest

from app.services.pii import detect_pii, redact_pii


class PiiTests(unittest.TestCase):
    def test_detects_and_redacts_common_pii(self) -> None:
        text = "Email admin@example.com or call +1 555-123-4567. SSN 123-45-6789."
        findings = detect_pii(text)
        self.assertGreaterEqual(findings["email"], 1)
        self.assertGreaterEqual(findings["phone"], 1)
        redacted = redact_pii(text)
        self.assertNotIn("admin@example.com", redacted)
        self.assertNotIn("123-45-6789", redacted)


if __name__ == "__main__":
    unittest.main()

