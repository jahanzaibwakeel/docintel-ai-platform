import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine, init_db
from app.main import app
from app.core.database import SessionLocal
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.ai import embed_text


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def reset_database() -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    init_db()


class ApiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_database()
        self.client = TestClient(app)
        self.settings = get_settings()
        self.original_email_outbox_dir = self.settings.email_outbox_dir
        self.original_email_provider = self.settings.email_provider

    def tearDown(self) -> None:
        self.settings.email_outbox_dir = self.original_email_outbox_dir
        self.settings.email_provider = self.original_email_provider

    def register(self, email: str = "ada@example.com", password: str = "strong-password") -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Ada Lovelace", "password": password},
        )
        self.assertEqual(response.status_code, 201, response.text)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_register_creates_personal_workspace_and_allows_me_lookup(self) -> None:
        headers = self.register()

        me = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["email"], "ada@example.com")

        workspaces = self.client.get("/api/v1/workspaces", headers=headers)
        self.assertEqual(workspaces.status_code, 200, workspaces.text)
        self.assertEqual(len(workspaces.json()), 1)
        self.assertEqual(workspaces.json()[0]["name"], "Ada Lovelace's Workspace")

    def test_ai_status_reports_provider_configuration(self) -> None:
        headers = self.register(email="ai-status@example.com")

        status_response = self.client.get("/api/v1/ai/status", headers=headers)
        self.assertEqual(status_response.status_code, 200, status_response.text)
        payload = status_response.json()
        self.assertEqual(payload["provider"], self.settings.ai_provider)
        self.assertIn("model", payload)
        self.assertIn("embedding_model", payload)
        self.assertEqual(payload["embedding_dimensions"], self.settings.embedding_dimensions)
        self.assertEqual(payload["max_context_chars"], self.settings.ai_max_context_chars)
        self.assertTrue(payload["configured"])

        health_response = self.client.get("/api/v1/ai/status?health_check=true", headers=headers)
        self.assertEqual(health_response.status_code, 200, health_response.text)
        self.assertTrue(health_response.json()["healthy"])

    def test_workspace_member_invite_sends_email(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)
            owner_headers = self.register(email="owner@example.com")
            member_headers = self.register(email="member@example.com")
            self.assertIn("Authorization", member_headers)
            workspaces = self.client.get("/api/v1/workspaces", headers=owner_headers)
            workspace_id = workspaces.json()[0]["id"]

            invite = self.client.post(
                f"/api/v1/workspaces/{workspace_id}/members",
                headers=owner_headers,
                json={"email": "member@example.com", "role": "member"},
            )
            self.assertEqual(invite.status_code, 201, invite.text)
            self.assertEqual(invite.json()["status"], "member")
            self.assertEqual(invite.json()["member"]["role"], "member")
            outbox = Path(outbox_dir) / "emails.jsonl"
            self.assertTrue(outbox.exists())
            outbox_text = outbox.read_text(encoding="utf-8")
            self.assertIn("member@example.com", outbox_text)
            self.assertIn("Ada Lovelace's Workspace", outbox_text)

    def test_workspace_admin_can_update_and_remove_members_safely(self) -> None:
        owner_headers = self.register(email="owner@example.com")
        admin_headers = self.register(email="admin@example.com")
        member_headers = self.register(email="member@example.com")
        workspaces = self.client.get("/api/v1/workspaces", headers=owner_headers)
        workspace_id = workspaces.json()[0]["id"]

        admin_add = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
            json={"email": "admin@example.com", "role": "admin"},
        )
        self.assertEqual(admin_add.status_code, 201, admin_add.text)
        admin_member_id = admin_add.json()["member"]["id"]

        member_add = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
            json={"email": "member@example.com", "role": "member"},
        )
        self.assertEqual(member_add.status_code, 201, member_add.text)
        member_id = member_add.json()["member"]["id"]

        listed = self.client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=owner_headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn("member@example.com", {member["user_email"] for member in listed.json()})

        promoted = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
            headers=owner_headers,
            json={"role": "viewer"},
        )
        self.assertEqual(promoted.status_code, 200, promoted.text)
        self.assertEqual(promoted.json()["role"], "viewer")

        removed = self.client.delete(f"/api/v1/workspaces/{workspace_id}/members/{member_id}", headers=admin_headers)
        self.assertEqual(removed.status_code, 204, removed.text)

        owner_member_id = next(member["id"] for member in listed.json() if member["role"] == "owner")
        demote_last_owner = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}/members/{owner_member_id}",
            headers=owner_headers,
            json={"role": "member"},
        )
        self.assertEqual(demote_last_owner.status_code, 409, demote_last_owner.text)

        remove_last_owner = self.client.delete(f"/api/v1/workspaces/{workspace_id}/members/{owner_member_id}", headers=owner_headers)
        self.assertEqual(remove_last_owner.status_code, 409, remove_last_owner.text)

        admin_removed = self.client.delete(f"/api/v1/workspaces/{workspace_id}/members/{admin_member_id}", headers=owner_headers)
        self.assertEqual(admin_removed.status_code, 204, admin_removed.text)

    def test_workspace_settings_rename_and_leave_keep_owner_protection(self) -> None:
        owner_headers = self.register(email="settings-owner@example.com")
        admin_headers = self.register(email="settings-admin@example.com")
        member_headers = self.register(email="settings-member@example.com")
        workspaces = self.client.get("/api/v1/workspaces", headers=owner_headers)
        workspace_id = workspaces.json()[0]["id"]

        renamed = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}",
            headers=owner_headers,
            json={"name": "Legal Review"},
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)
        self.assertEqual(renamed.json()["name"], "Legal Review")

        admin_add = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
            json={"email": "settings-admin@example.com", "role": "admin"},
        )
        self.assertEqual(admin_add.status_code, 201, admin_add.text)

        admin_rename = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}",
            headers=admin_headers,
            json={"name": "Contract Review"},
        )
        self.assertEqual(admin_rename.status_code, 200, admin_rename.text)
        self.assertEqual(admin_rename.json()["name"], "Contract Review")

        member_add = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
            json={"email": "settings-member@example.com", "role": "member"},
        )
        self.assertEqual(member_add.status_code, 201, member_add.text)

        member_rename = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}",
            headers=member_headers,
            json={"name": "Member Rename"},
        )
        self.assertEqual(member_rename.status_code, 403, member_rename.text)

        member_leave = self.client.post(f"/api/v1/workspaces/{workspace_id}/leave", headers=member_headers)
        self.assertEqual(member_leave.status_code, 204, member_leave.text)
        member_workspaces = self.client.get("/api/v1/workspaces", headers=member_headers)
        self.assertNotIn(workspace_id, {workspace["id"] for workspace in member_workspaces.json()})

        last_owner_leave = self.client.post(f"/api/v1/workspaces/{workspace_id}/leave", headers=owner_headers)
        self.assertEqual(last_owner_leave.status_code, 409, last_owner_leave.text)

    def test_collections_annotations_and_bulk_document_actions(self) -> None:
        headers = self.register(email="organizer@example.com")
        workspace_id = self.client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
        with patch("app.api.routes.documents.process_document.delay"):
            first = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("first.pdf", PDF_BYTES, "application/pdf")},
            ).json()
            second = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("second.pdf", PDF_BYTES, "application/pdf")},
            ).json()

        with SessionLocal() as db:
            for payload in (first, second):
                document = db.get(Document, payload["id"])
                self.assertIsNotNone(document)
                document.status = DocumentStatus.ready
                document.extracted_text = f"{document.filename} includes renewal and review language."
                db.add(DocumentChunk(document_id=document.id, chunk_index=0, page_number=1, text=document.extracted_text, embedding=embed_text(document.extracted_text)))
            db.commit()

        created_collection = self.client.post(
            "/api/v1/collections",
            headers=headers,
            json={"workspace_id": workspace_id, "name": "Due diligence", "description": "Deal room files"},
        )
        self.assertEqual(created_collection.status_code, 201, created_collection.text)
        collection_id = created_collection.json()["id"]

        collections = self.client.get(f"/api/v1/collections?workspace_id={workspace_id}", headers=headers)
        self.assertEqual(collections.status_code, 200, collections.text)
        self.assertEqual([collection["name"] for collection in collections.json()], ["Due diligence"])

        bulk = self.client.post(
            "/api/v1/documents/bulk",
            headers=headers,
            json={
                "document_ids": [first["id"], second["id"]],
                "tags_add": ["Deal", "review"],
                "favorite": True,
                "review_status": "in_review",
                "collection_id": collection_id,
            },
        )
        self.assertEqual(bulk.status_code, 200, bulk.text)
        self.assertEqual(bulk.json()["updated"], 2)
        self.assertEqual({document["collection_id"] for document in bulk.json()["documents"]}, {collection_id})

        collection_docs = self.client.get(f"/api/v1/documents?collection_id={collection_id}", headers=headers)
        self.assertEqual(collection_docs.status_code, 200, collection_docs.text)
        self.assertEqual({document["filename"] for document in collection_docs.json()}, {"first.pdf", "second.pdf"})
        self.assertTrue(all(document["favorite"] for document in collection_docs.json()))

        search = self.client.post(
            "/api/v1/search",
            headers=headers,
            json={"query": "renewal review", "collection_id": collection_id, "limit": 5},
        )
        self.assertEqual(search.status_code, 200, search.text)
        self.assertEqual({result["filename"] for result in search.json()["results"]}, {"first.pdf", "second.pdf"})

        annotation = self.client.post(
            f"/api/v1/documents/{first['id']}/annotations",
            headers=headers,
            json={"page_number": 1, "quote_text": "renewal", "note": "Check renewal clause", "color": "yellow"},
        )
        self.assertEqual(annotation.status_code, 201, annotation.text)
        annotation_id = annotation.json()["id"]

        annotations = self.client.get(f"/api/v1/documents/{first['id']}/annotations", headers=headers)
        self.assertEqual(annotations.status_code, 200, annotations.text)
        self.assertEqual(annotations.json()[0]["note"], "Check renewal clause")

        deleted = self.client.delete(f"/api/v1/documents/{first['id']}/annotations/{annotation_id}", headers=headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)

        after_delete = self.client.get(f"/api/v1/documents/{first['id']}/annotations", headers=headers)
        self.assertEqual(after_delete.status_code, 200, after_delete.text)
        self.assertEqual(after_delete.json(), [])

    def test_workspace_quotas_and_document_permissions(self) -> None:
        owner_headers = self.register(email="quota-owner@example.com")
        viewer_headers = self.register(email="quota-viewer@example.com")
        workspace_id = self.client.get("/api/v1/workspaces", headers=owner_headers).json()[0]["id"]

        added = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
            json={"email": "quota-viewer@example.com", "role": "viewer"},
        )
        self.assertEqual(added.status_code, 201, added.text)

        quota = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}/quota",
            headers=owner_headers,
            json={"document_quota": 1, "page_quota": 10, "storage_quota_mb": 1},
        )
        self.assertEqual(quota.status_code, 200, quota.text)
        self.assertEqual(quota.json()["document_quota"], 1)

        with patch("app.api.routes.documents.process_document.delay"):
            first = self.client.post(
                f"/api/v1/documents?workspace_id={workspace_id}",
                headers=owner_headers,
                files={"file": ("quota.pdf", PDF_BYTES, "application/pdf")},
            )
            self.assertEqual(first.status_code, 201, first.text)
            blocked = self.client.post(
                f"/api/v1/documents?workspace_id={workspace_id}",
                headers=owner_headers,
                files={"file": ("blocked.pdf", PDF_BYTES, "application/pdf")},
            )
        self.assertEqual(blocked.status_code, 409, blocked.text)

        usage = self.client.get(f"/api/v1/workspaces/{workspace_id}/usage", headers=owner_headers)
        self.assertEqual(usage.status_code, 200, usage.text)
        self.assertEqual(usage.json()["document_count"], 1)
        document_id = first.json()["id"]

        forbidden_annotation = self.client.post(
            f"/api/v1/documents/{document_id}/annotations",
            headers=viewer_headers,
            json={"page_number": 1, "note": "Needs access"},
        )
        self.assertEqual(forbidden_annotation.status_code, 403, forbidden_annotation.text)

        permission = self.client.post(
            f"/api/v1/documents/{document_id}/permissions",
            headers=owner_headers,
            json={"email": "quota-viewer@example.com", "role": "commenter"},
        )
        self.assertEqual(permission.status_code, 201, permission.text)
        self.assertEqual(permission.json()["role"], "commenter")

        allowed_annotation = self.client.post(
            f"/api/v1/documents/{document_id}/annotations",
            headers=viewer_headers,
            json={"page_number": 1, "note": "Allowed comment"},
        )
        self.assertEqual(allowed_annotation.status_code, 201, allowed_annotation.text)

        forbidden_edit = self.client.patch(
            f"/api/v1/documents/{document_id}/organization",
            headers=viewer_headers,
            json={"tags": ["viewer"], "favorite": True},
        )
        self.assertEqual(forbidden_edit.status_code, 403, forbidden_edit.text)

        editor_permission = self.client.post(
            f"/api/v1/documents/{document_id}/permissions",
            headers=owner_headers,
            json={"email": "quota-viewer@example.com", "role": "editor"},
        )
        self.assertEqual(editor_permission.status_code, 201, editor_permission.text)

        allowed_edit = self.client.patch(
            f"/api/v1/documents/{document_id}/organization",
            headers=viewer_headers,
            json={"tags": ["viewer"], "favorite": True},
        )
        self.assertEqual(allowed_edit.status_code, 200, allowed_edit.text)
        self.assertEqual(allowed_edit.json()["tags"], ["viewer"])

    def test_saved_searches_are_user_owned_and_workspace_scoped(self) -> None:
        owner_headers = self.register(email="saved-owner@example.com")
        other_headers = self.register(email="saved-other@example.com")
        workspace_id = self.client.get("/api/v1/workspaces", headers=owner_headers).json()[0]["id"]

        created = self.client.post(
            "/api/v1/saved-searches",
            headers=owner_headers,
            json={
                "name": "Approved renewals",
                "query": "automatic renewal",
                "workspace_id": workspace_id,
                "filters": {"reviewStatus": "approved", "tag": "renewal", "favorite": True},
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        saved_search = created.json()
        self.assertEqual(saved_search["workspace_id"], workspace_id)
        self.assertEqual(saved_search["filters"]["reviewStatus"], "approved")

        listed = self.client.get(f"/api/v1/saved-searches?workspace_id={workspace_id}", headers=owner_headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual([item["name"] for item in listed.json()], ["Approved renewals"])

        hidden = self.client.get("/api/v1/saved-searches", headers=other_headers)
        self.assertEqual(hidden.status_code, 200, hidden.text)
        self.assertEqual(hidden.json(), [])

        forbidden_update = self.client.patch(
            f"/api/v1/saved-searches/{saved_search['id']}",
            headers=other_headers,
            json={"name": "Nope", "query": "nope", "workspace_id": None, "filters": {}},
        )
        self.assertEqual(forbidden_update.status_code, 404, forbidden_update.text)

        updated = self.client.patch(
            f"/api/v1/saved-searches/{saved_search['id']}",
            headers=owner_headers,
            json={
                "name": "High risk contracts",
                "query": "liability",
                "workspace_id": workspace_id,
                "filters": {"riskSeverity": "high"},
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["name"], "High risk contracts")
        self.assertEqual(updated.json()["filters"], {"riskSeverity": "high"})

        deleted = self.client.delete(f"/api/v1/saved-searches/{saved_search['id']}", headers=owner_headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)

        after_delete = self.client.get("/api/v1/saved-searches", headers=owner_headers)
        self.assertEqual(after_delete.status_code, 200, after_delete.text)
        self.assertEqual(after_delete.json(), [])

    def test_workspace_invitation_can_be_accepted_by_matching_email(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)
            owner_headers = self.register(email="owner@example.com")
            workspaces = self.client.get("/api/v1/workspaces", headers=owner_headers)
            workspace_id = workspaces.json()[0]["id"]

            invite = self.client.post(
                f"/api/v1/workspaces/{workspace_id}/members",
                headers=owner_headers,
                json={"email": "newmember@example.com", "role": "viewer"},
            )
            self.assertEqual(invite.status_code, 201, invite.text)
            self.assertEqual(invite.json()["status"], "invited")
            self.assertEqual(invite.json()["invitation"]["email"], "newmember@example.com")
            outbox_payload = json.loads((Path(outbox_dir) / "emails.jsonl").read_text(encoding="utf-8").strip())
            invite_url = next(line for line in outbox_payload["text"].splitlines() if "invite_token=" in line)
            token = parse_qs(urlparse(invite_url).query)["invite_token"][0]

            member_headers = self.register(email="newmember@example.com")
            accepted = self.client.post("/api/v1/workspaces/invitations/accept", headers=member_headers, json={"token": token})
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertEqual(accepted.json()["workspace_id"], workspace_id)
            self.assertEqual(accepted.json()["role"], "viewer")

            reused = self.client.post("/api/v1/workspaces/invitations/accept", headers=member_headers, json={"token": token})
            self.assertEqual(reused.status_code, 401, reused.text)

    def test_workspace_admin_can_list_resend_and_revoke_invitations(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)
            owner_headers = self.register(email="owner@example.com")
            workspaces = self.client.get("/api/v1/workspaces", headers=owner_headers)
            workspace_id = workspaces.json()[0]["id"]

            invite = self.client.post(
                f"/api/v1/workspaces/{workspace_id}/members",
                headers=owner_headers,
                json={"email": "pending@example.com", "role": "member"},
            )
            self.assertEqual(invite.status_code, 201, invite.text)
            invitation_id = invite.json()["invitation"]["id"]
            first_payload = json.loads((Path(outbox_dir) / "emails.jsonl").read_text(encoding="utf-8").strip())
            first_url = next(line for line in first_payload["text"].splitlines() if "invite_token=" in line)
            first_token = parse_qs(urlparse(first_url).query)["invite_token"][0]

            listed = self.client.get(f"/api/v1/workspaces/{workspace_id}/invitations", headers=owner_headers)
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(listed.json()["pending_count"], 1)
            self.assertEqual(listed.json()["invitations"][0]["email"], "pending@example.com")

            resent = self.client.post(
                f"/api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/resend",
                headers=owner_headers,
            )
            self.assertEqual(resent.status_code, 200, resent.text)
            outbox_lines = (Path(outbox_dir) / "emails.jsonl").read_text(encoding="utf-8").strip().splitlines()
            second_payload = json.loads(outbox_lines[-1])
            second_url = next(line for line in second_payload["text"].splitlines() if "invite_token=" in line)
            second_token = parse_qs(urlparse(second_url).query)["invite_token"][0]
            self.assertNotEqual(second_token, first_token)

            member_headers = self.register(email="pending@example.com")
            old_accept = self.client.post("/api/v1/workspaces/invitations/accept", headers=member_headers, json={"token": first_token})
            self.assertEqual(old_accept.status_code, 401, old_accept.text)

            revoked = self.client.post(
                f"/api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/revoke",
                headers=owner_headers,
            )
            self.assertEqual(revoked.status_code, 200, revoked.text)
            self.assertIsNotNone(revoked.json()["revoked_at"])

            revoked_accept = self.client.post("/api/v1/workspaces/invitations/accept", headers=member_headers, json={"token": second_token})
            self.assertEqual(revoked_accept.status_code, 401, revoked_accept.text)

    def test_duplicate_registration_and_bad_login_return_clean_errors(self) -> None:
        self.register()

        duplicate = self.client.post(
            "/api/v1/auth/register",
            json={"email": "ADA@example.com", "full_name": "Ada Again", "password": "strong-password"},
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertIn("detail", duplicate.json())

        bad_login = self.client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": "wrong-password"})
        self.assertEqual(bad_login.status_code, 401, bad_login.text)
        self.assertIn("detail", bad_login.json())

    def test_profile_update_and_password_change_revoke_refresh_sessions(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "profile@example.com", "full_name": "Profile User", "password": "strong-password"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        updated = self.client.patch("/api/v1/auth/me", headers=headers, json={"full_name": "Updated Profile"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["full_name"], "Updated Profile")

        wrong_password = self.client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "wrong-password", "new_password": "new-strong-password"},
        )
        self.assertEqual(wrong_password.status_code, 401, wrong_password.text)

        changed = self.client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "strong-password", "new_password": "new-strong-password"},
        )
        self.assertEqual(changed.status_code, 204, changed.text)

        old_login = self.client.post("/api/v1/auth/login", json={"email": "profile@example.com", "password": "strong-password"})
        self.assertEqual(old_login.status_code, 401, old_login.text)

        new_login = self.client.post("/api/v1/auth/login", json={"email": "profile@example.com", "password": "new-strong-password"})
        self.assertEqual(new_login.status_code, 200, new_login.text)

        old_refresh = self.client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        self.assertEqual(old_refresh.status_code, 401, old_refresh.text)

    def test_refresh_token_rotates_and_logout_revokes_session(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "session@example.com", "full_name": "Session User", "password": "strong-password"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        tokens = response.json()
        self.assertIn("refresh_token", tokens)

        refreshed = self.client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        rotated = refreshed.json()
        self.assertNotEqual(rotated["refresh_token"], tokens["refresh_token"])

        reused = self.client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        self.assertEqual(reused.status_code, 401, reused.text)

        logout = self.client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {rotated['access_token']}"},
            json={"refresh_token": rotated["refresh_token"]},
        )
        self.assertEqual(logout.status_code, 204, logout.text)

        after_logout = self.client.post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
        self.assertEqual(after_logout.status_code, 401, after_logout.text)

    def test_password_reset_changes_password_and_revokes_refresh_sessions(self) -> None:
        with TemporaryDirectory() as outbox_dir:
            self.settings.email_provider = "outbox"
            self.settings.email_outbox_dir = Path(outbox_dir)
            response = self.client.post(
                "/api/v1/auth/register",
                json={"email": "reset@example.com", "full_name": "Reset User", "password": "strong-password"},
            )
            self.assertEqual(response.status_code, 201, response.text)
            original_refresh_token = response.json()["refresh_token"]

            unknown = self.client.post("/api/v1/auth/password-reset/request", json={"email": "missing@example.com"})
            self.assertEqual(unknown.status_code, 200, unknown.text)
            self.assertIsNone(unknown.json()["reset_token"])

            reset = self.client.post("/api/v1/auth/password-reset/request", json={"email": "RESET@example.com"})
            self.assertEqual(reset.status_code, 200, reset.text)
            reset_token = reset.json()["reset_token"]
            self.assertIsInstance(reset_token, str)
            self.assertGreater(len(reset_token), 30)
            outbox = Path(outbox_dir) / "emails.jsonl"
            self.assertTrue(outbox.exists())
            outbox_text = outbox.read_text(encoding="utf-8")
            self.assertIn("reset_token=", outbox_text)
            self.assertIn("reset@example.com", outbox_text)

            confirm = self.client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": reset_token, "new_password": "new-strong-password"},
            )
            self.assertEqual(confirm.status_code, 204, confirm.text)

            old_login = self.client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "strong-password"})
            self.assertEqual(old_login.status_code, 401, old_login.text)

            new_login = self.client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "new-strong-password"})
            self.assertEqual(new_login.status_code, 200, new_login.text)

            reused = self.client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": reset_token, "new_password": "another-strong-password"},
            )
            self.assertEqual(reused.status_code, 401, reused.text)

            revoked_refresh = self.client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh_token})
            self.assertEqual(revoked_refresh.status_code, 401, revoked_refresh.text)

    def test_upload_validates_auth_and_pdf_content_then_lists_document(self) -> None:
        unauthenticated = self.client.get("/api/v1/documents")
        self.assertEqual(unauthenticated.status_code, 401, unauthenticated.text)

        headers = self.register()

        bad_upload = self.client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(bad_upload.status_code, 400, bad_upload.text)

        with patch("app.api.routes.documents.process_document.delay") as enqueue:
            upload = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("contract.pdf", PDF_BYTES, "application/pdf")},
            )

        self.assertEqual(upload.status_code, 201, upload.text)
        document = upload.json()
        self.assertEqual(document["filename"], "contract.pdf")
        self.assertEqual(document["status"], "uploaded")
        self.assertEqual(document["file_size_bytes"], len(PDF_BYTES))
        enqueue.assert_called_once_with(document["id"])

        documents = self.client.get("/api/v1/documents", headers=headers)
        self.assertEqual(documents.status_code, 200, documents.text)
        self.assertEqual([item["id"] for item in documents.json()], [document["id"]])

        json_export = self.client.get(f"/api/v1/documents/{document['id']}/export?format=json", headers=headers)
        self.assertEqual(json_export.status_code, 200, json_export.text)
        self.assertIn('filename="contract.json"', json_export.headers["content-disposition"])
        self.assertEqual(json_export.json()["filename"], "contract.pdf")
        self.assertIn("extracted_text", json_export.json())

        markdown_export = self.client.get(f"/api/v1/documents/{document['id']}/export?format=markdown", headers=headers)
        self.assertEqual(markdown_export.status_code, 200, markdown_export.text)
        self.assertIn('filename="contract.md"', markdown_export.headers["content-disposition"])
        self.assertIn("# contract.pdf", markdown_export.text)

    def test_compare_documents_reports_field_risk_and_text_changes(self) -> None:
        headers = self.register()
        with patch("app.api.routes.documents.process_document.delay"):
            left = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("msa-2025.pdf", PDF_BYTES, "application/pdf")},
            ).json()
            right = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("msa-2026.pdf", PDF_BYTES, "application/pdf")},
            ).json()

        with SessionLocal() as db:
            left_doc = db.get(Document, left["id"])
            right_doc = db.get(Document, right["id"])
            self.assertIsNotNone(left_doc)
            self.assertIsNotNone(right_doc)
            left_doc.status = DocumentStatus.ready
            left_doc.summary = "Agreement with Acme for monthly support."
            left_doc.extracted_text = "Acme agrees to monthly support with a cap on liability."
            left_doc.key_fields = {"organizations": ["Acme"], "amounts": ["$10,000"]}
            left_doc.risk_flags = [{"label": "Liability cap", "severity": "medium", "confidence": 80, "evidence": "cap on liability"}]
            right_doc.status = DocumentStatus.ready
            right_doc.summary = "Agreement with Globex for annual support."
            right_doc.extracted_text = "Globex agrees to annual support with automatic renewal."
            right_doc.key_fields = {"organizations": ["Globex"], "amounts": ["$12,000"]}
            right_doc.risk_flags = [{"label": "Auto renewal", "severity": "high", "confidence": 90, "evidence": "automatic renewal"}]
            db.commit()

        response = self.client.post(
            f"/api/v1/documents/{left['id']}/compare",
            headers=headers,
            json={"other_document_id": right["id"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        comparison = response.json()
        self.assertEqual(comparison["left"]["filename"], "msa-2025.pdf")
        self.assertEqual(comparison["right"]["filename"], "msa-2026.pdf")
        self.assertLess(comparison["similarity"], 1)
        self.assertEqual(comparison["field_changes"]["organizations"]["only_in_left"], ["Acme"])
        self.assertEqual(comparison["field_changes"]["organizations"]["only_in_right"], ["Globex"])
        self.assertEqual(comparison["risk_changes"]["only_in_left"], ["Liability cap"])
        self.assertEqual(comparison["risk_changes"]["only_in_right"], ["Auto renewal"])

    def test_document_and_search_filters_return_matching_documents(self) -> None:
        headers = self.register()
        with patch("app.api.routes.documents.process_document.delay"):
            invoice = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("invoice.pdf", PDF_BYTES, "application/pdf")},
            ).json()
            contract = self.client.post(
                "/api/v1/documents",
                headers=headers,
                files={"file": ("contract.pdf", PDF_BYTES, "application/pdf")},
            ).json()

        with SessionLocal() as db:
            invoice_doc = db.get(Document, invoice["id"])
            contract_doc = db.get(Document, contract["id"])
            self.assertIsNotNone(invoice_doc)
            self.assertIsNotNone(contract_doc)
            invoice_doc.status = DocumentStatus.ready
            invoice_doc.document_type = "invoice"
            invoice_doc.summary = "Invoice for platform services."
            invoice_doc.extracted_text = "Invoice payment due for platform services."
            invoice_doc.risk_flags = [{"label": "Late fee", "severity": "low", "confidence": 60, "evidence": "late fee"}]
            contract_doc.status = DocumentStatus.ready
            contract_doc.document_type = "contract"
            contract_doc.summary = "Contract with automatic renewal."
            contract_doc.extracted_text = "Contract includes automatic renewal and termination notice."
            contract_doc.risk_flags = [{"label": "Auto renewal", "severity": "high", "confidence": 90, "evidence": "automatic renewal"}]
            db.add(DocumentChunk(document_id=invoice_doc.id, chunk_index=0, page_number=1, text=invoice_doc.extracted_text, embedding=embed_text(invoice_doc.extracted_text)))
            db.add(DocumentChunk(document_id=contract_doc.id, chunk_index=0, page_number=1, text=contract_doc.extracted_text, embedding=embed_text(contract_doc.extracted_text)))
            db.commit()

        list_response = self.client.get("/api/v1/documents?document_type=contract&status=ready", headers=headers)
        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual([item["filename"] for item in list_response.json()], ["contract.pdf"])

        search_response = self.client.post(
            "/api/v1/search",
            headers=headers,
            json={"query": "automatic renewal", "document_type": "contract", "risk_severity": "high", "limit": 5},
        )
        self.assertEqual(search_response.status_code, 200, search_response.text)
        results = search_response.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual({result["filename"] for result in results}, {"contract.pdf"})

        organized = self.client.patch(
            f"/api/v1/documents/{contract['id']}/organization",
            headers=headers,
            json={"tags": [" Legal ", "Renewal", "legal"], "favorite": True},
        )
        self.assertEqual(organized.status_code, 200, organized.text)
        self.assertEqual(organized.json()["tags"], ["legal", "renewal"])
        self.assertTrue(organized.json()["favorite"])

        tagged_list = self.client.get("/api/v1/documents?tag=legal&favorite=true", headers=headers)
        self.assertEqual(tagged_list.status_code, 200, tagged_list.text)
        self.assertEqual([item["filename"] for item in tagged_list.json()], ["contract.pdf"])

        tagged_search = self.client.post(
            "/api/v1/search",
            headers=headers,
            json={"query": "automatic renewal", "tag": "renewal", "favorite": True, "limit": 5},
        )
        self.assertEqual(tagged_search.status_code, 200, tagged_search.text)
        self.assertEqual({result["filename"] for result in tagged_search.json()["results"]}, {"contract.pdf"})

        reviewed = self.client.patch(
            f"/api/v1/documents/{contract['id']}/review",
            headers=headers,
            json={"title": "Renewal Contract", "review_status": "approved", "review_notes": "Reviewed by legal."},
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["title"], "Renewal Contract")
        self.assertEqual(reviewed.json()["review_status"], "approved")
        self.assertEqual(reviewed.json()["review_notes"], "Reviewed by legal.")

        reviewed_list = self.client.get("/api/v1/documents?review_status=approved", headers=headers)
        self.assertEqual(reviewed_list.status_code, 200, reviewed_list.text)
        self.assertEqual([item["title"] for item in reviewed_list.json()], ["Renewal Contract"])

        reviewed_search = self.client.post(
            "/api/v1/search",
            headers=headers,
            json={"query": "automatic renewal", "review_status": "approved", "limit": 5},
        )
        self.assertEqual(reviewed_search.status_code, 200, reviewed_search.text)
        self.assertEqual({result["filename"] for result in reviewed_search.json()["results"]}, {"contract.pdf"})

        reviewed_export = self.client.get(f"/api/v1/documents/{contract['id']}/export?format=json", headers=headers)
        self.assertEqual(reviewed_export.status_code, 200, reviewed_export.text)
        self.assertEqual(reviewed_export.json()["review_status"], "approved")
        self.assertEqual(reviewed_export.json()["review_notes"], "Reviewed by legal.")


if __name__ == "__main__":
    unittest.main()
