import unittest

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal, engine, init_db
from app.main import app
from app.models.notification import Notification


def reset_database() -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    init_db()


class NotificationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)

    def register(self, email: str) -> tuple[int, dict[str, str]]:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Notify User", "password": "strong-password"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        user = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(user.status_code, 200, user.text)
        return user.json()["id"], headers

    def test_user_can_list_and_mark_own_notifications_read(self) -> None:
        user_id, headers = self.register("notify@example.com")
        with SessionLocal() as db:
            notification = Notification(
                user_id=user_id,
                kind="document.ready",
                title="Document ready",
                message="contract.pdf has finished processing.",
            )
            db.add(notification)
            db.commit()
            notification_id = notification.id

        listed = self.client.get("/api/v1/notifications", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["unread_count"], 1)
        self.assertEqual(listed.json()["notifications"][0]["title"], "Document ready")

        marked = self.client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
        self.assertEqual(marked.status_code, 204, marked.text)

        unread = self.client.get("/api/v1/notifications?unread_only=true", headers=headers)
        self.assertEqual(unread.status_code, 200, unread.text)
        self.assertEqual(unread.json()["unread_count"], 0)
        self.assertEqual(unread.json()["notifications"], [])

    def test_user_cannot_mark_another_users_notification_read(self) -> None:
        first_user_id, _ = self.register("first@example.com")
        _, second_headers = self.register("second@example.com")
        with SessionLocal() as db:
            notification = Notification(user_id=first_user_id, kind="system", title="Private", message="Private")
            db.add(notification)
            db.commit()
            notification_id = notification.id

        response = self.client.post(f"/api/v1/notifications/{notification_id}/read", headers=second_headers)
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()
