import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal, engine, init_db
from app.models.document import Document, DocumentStatus
from app.main import app
from tests.test_api_workflow import PDF_BYTES


def reset_database() -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    init_db()


class AdminTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.settings = get_settings()
        self.original_admin_emails = self.settings.admin_emails
        self.settings.admin_emails = "admin@example.com"

    def tearDown(self) -> None:
        self.settings.admin_emails = self.original_admin_emails

    def register(self, email: str) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Admin User", "password": "strong-password"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_admin_endpoints_require_configured_admin_email(self) -> None:
        user_headers = self.register("user@example.com")
        forbidden = self.client.get("/api/v1/admin/stats", headers=user_headers)
        self.assertEqual(forbidden.status_code, 403, forbidden.text)

    def test_admin_can_view_stats_users_workspaces_and_failed_documents(self) -> None:
        headers = self.register("admin@example.com")
        with patch("app.api.routes.documents.process_document.delay"):
            uploaded = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("broken.pdf", PDF_BYTES, "application/pdf")},
            )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        document_id = uploaded.json()["id"]
        with SessionLocal() as db:
            document = db.get(Document, document_id)
            self.assertIsNotNone(document)
            document.status = DocumentStatus.failed
            document.error_message = "OCR timeout"
            db.commit()

        stats = self.client.get("/api/v1/admin/stats", headers=headers)
        self.assertEqual(stats.status_code, 200, stats.text)
        self.assertEqual(stats.json()["users"], 1)
        self.assertEqual(stats.json()["failed_documents"], 1)

        users = self.client.get("/api/v1/admin/users", headers=headers)
        self.assertEqual(users.status_code, 200, users.text)
        self.assertEqual(users.json()[0]["email"], "admin@example.com")

        workspaces = self.client.get("/api/v1/admin/workspaces", headers=headers)
        self.assertEqual(workspaces.status_code, 200, workspaces.text)
        self.assertEqual(workspaces.json()[0]["member_count"], 1)

        failed = self.client.get("/api/v1/admin/documents?failed_only=true", headers=headers)
        self.assertEqual(failed.status_code, 200, failed.text)
        self.assertEqual(failed.json()[0]["filename"], "broken.pdf")
        self.assertEqual(failed.json()[0]["error_message"], "OCR timeout")

        ops = self.client.get("/api/v1/admin/ops/health", headers=headers)
        self.assertEqual(ops.status_code, 200, ops.text)
        self.assertEqual(ops.json()["status"], "degraded")
        self.assertEqual(ops.json()["failed_documents"], 1)
        self.assertEqual(ops.json()["recent_failures"][0]["filename"], "broken.pdf")
        self.assertIn("metrics", ops.json())


if __name__ == "__main__":
    unittest.main()
