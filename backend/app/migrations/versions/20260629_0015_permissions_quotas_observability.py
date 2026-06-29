"""add document permissions and workspace quotas

Revision ID: 20260629_0015
Revises: 20260629_0014
Create Date: 2026-06-29 00:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0015"
down_revision: str | None = "20260629_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    access_role = postgresql.ENUM("viewer", "commenter", "editor", name="documentaccessrole", create_type=False)
    access_role.create(op.get_bind(), checkfirst=True)

    op.add_column("workspaces", sa.Column("document_quota", sa.Integer(), nullable=True))
    op.add_column("workspaces", sa.Column("page_quota", sa.Integer(), nullable=True))
    op.add_column("workspaces", sa.Column("storage_quota_mb", sa.Integer(), nullable=True))

    op.create_table(
        "document_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", access_role, nullable=False),
        sa.Column("granted_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "user_id", name="uq_document_permissions_document_user"),
    )
    op.create_index(op.f("ix_document_permissions_id"), "document_permissions", ["id"], unique=False)
    op.create_index(op.f("ix_document_permissions_document_id"), "document_permissions", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_permissions_user_id"), "document_permissions", ["user_id"], unique=False)
    op.create_index(op.f("ix_document_permissions_role"), "document_permissions", ["role"], unique=False)
    op.create_index(op.f("ix_document_permissions_granted_by_id"), "document_permissions", ["granted_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_permissions_granted_by_id"), table_name="document_permissions")
    op.drop_index(op.f("ix_document_permissions_role"), table_name="document_permissions")
    op.drop_index(op.f("ix_document_permissions_user_id"), table_name="document_permissions")
    op.drop_index(op.f("ix_document_permissions_document_id"), table_name="document_permissions")
    op.drop_index(op.f("ix_document_permissions_id"), table_name="document_permissions")
    op.drop_table("document_permissions")

    op.drop_column("workspaces", "storage_quota_mb")
    op.drop_column("workspaces", "page_quota")
    op.drop_column("workspaces", "document_quota")

    access_role = postgresql.ENUM("viewer", "commenter", "editor", name="documentaccessrole", create_type=False)
    access_role.drop(op.get_bind(), checkfirst=True)
