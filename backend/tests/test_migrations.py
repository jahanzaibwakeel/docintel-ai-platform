import unittest

from sqlalchemy import inspect, text

from app.core.database import engine, init_db


class MigrationTests(unittest.TestCase):
    def test_migrations_create_expected_tables_and_pgvector(self) -> None:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO public"))

        init_db()
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertIn("users", tables)
        self.assertIn("documents", tables)
        self.assertIn("document_chunks", tables)
        self.assertIn("workspaces", tables)
        self.assertIn("audit_logs", tables)
        self.assertIn("notifications", tables)
        self.assertIn("refresh_tokens", tables)
        self.assertIn("password_reset_tokens", tables)
        self.assertIn("workspace_invitations", tables)
        self.assertIn("saved_searches", tables)
        self.assertIn("document_collections", tables)
        self.assertIn("document_annotations", tables)
        columns = {column["name"] for column in inspector.get_columns("documents")}
        self.assertIn("tags", columns)
        self.assertIn("favorite", columns)
        self.assertIn("title", columns)
        self.assertIn("review_status", columns)
        self.assertIn("review_notes", columns)
        self.assertIn("collection_id", columns)
        with engine.connect() as connection:
            installed = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
        self.assertEqual(installed, "vector")


if __name__ == "__main__":
    unittest.main()
