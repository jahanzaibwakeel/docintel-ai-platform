"""add document retention lifecycle fields

Revision ID: 20260622_0006
Revises: 20260621_0005
Create Date: 2026-06-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_0006"
down_revision: str | None = "20260621_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'deleted'")
    op.add_column("documents", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("deleted_by_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_documents_deleted_by_id", "documents", "users", ["deleted_by_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_documents_retention_expires_at"), "documents", ["retention_expires_at"], unique=False)
    op.create_index(op.f("ix_documents_deleted_at"), "documents", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_deleted_at"), table_name="documents")
    op.drop_index(op.f("ix_documents_retention_expires_at"), table_name="documents")
    op.drop_constraint("fk_documents_deleted_by_id", "documents", type_="foreignkey")
    op.drop_column("documents", "deleted_by_id")
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "retention_expires_at")

