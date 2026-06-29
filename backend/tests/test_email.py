import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.config import get_settings
from app.services.email import (
    EmailMessage,
    build_password_reset_url,
    send_email,
    send_workspace_invitation_email,
    send_workspace_member_email,
)


class EmailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.original_email_provider = self.settings.email_provider
        self.original_email_outbox_dir = self.settings.email_outbox_dir
        self.original_frontend_origin = self.settings.frontend_origin

    def tearDown(self) -> None:
        self.settings.email_provider = self.original_email_provider
        self.settings.email_outbox_dir = self.original_email_outbox_dir
        self.settings.frontend_origin = self.original_frontend_origin

    def test_outbox_provider_writes_email_jsonl(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)

            send_email(EmailMessage(to="ada@example.com", subject="Hello", text="Body", html="<p>Body</p>"))

            outbox = Path(outbox_dir) / "emails.jsonl"
            self.assertTrue(outbox.exists())
            payload = json.loads(outbox.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["to"], "ada@example.com")
            self.assertEqual(payload["subject"], "Hello")
            self.assertEqual(payload["text"], "Body")
            self.assertIn("created_at", payload)

    def test_password_reset_url_uses_frontend_origin(self) -> None:
        self.settings.frontend_origin = "https://docs.example.test"

        reset_url = build_password_reset_url("abc 123")

        self.assertEqual(reset_url, "https://docs.example.test/?reset_token=abc+123")

    def test_workspace_member_email_uses_outbox_provider(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)
            self.settings.frontend_origin = "https://docs.example.test"

            send_workspace_member_email("grace@example.com", "Legal Team", "member", "ada@example.com")

            outbox = Path(outbox_dir) / "emails.jsonl"
            payload = json.loads(outbox.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["to"], "grace@example.com")
            self.assertIn("Legal Team", payload["subject"])
            self.assertIn("ada@example.com", payload["text"])
            self.assertIn("https://docs.example.test", payload["text"])

    def test_workspace_invitation_email_contains_invite_token(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)
            self.settings.frontend_origin = "https://docs.example.test"

            send_workspace_invitation_email("grace@example.com", "Legal Team", "viewer", "ada@example.com", "invite-123")

            outbox = Path(outbox_dir) / "emails.jsonl"
            payload = json.loads(outbox.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["to"], "grace@example.com")
            self.assertIn("invited", payload["text"])
            self.assertIn("invite_token=invite-123", payload["text"])


if __name__ == "__main__":
    unittest.main()
