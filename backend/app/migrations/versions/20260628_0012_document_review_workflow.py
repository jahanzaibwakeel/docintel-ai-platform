"""add document review workflow

Revision ID: 20260628_0012
Revises: 20260628_0011
Create Date: 2026-06-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260628_0012"
down_revision: str | None = "20260628_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


review_status = postgresql.ENUM("unreviewed", "in_review", "approved", "needs_changes", name="documentreviewstatus")


def upgrade() -> None:
    review_status.create(op.get_bind(), checkfirst=True)
    op.add_column("documents", sa.Column("title", sa.String(length=512), nullable=True))
    op.add_column("documents", sa.Column("review_status", review_status, server_default="unreviewed", nullable=False))
    op.add_column("documents", sa.Column("review_notes", sa.Text(), nullable=True))
    op.create_index(op.f("ix_documents_title"), "documents", ["title"], unique=False)
    op.create_index(op.f("ix_documents_review_status"), "documents", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_review_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_title"), table_name="documents")
    op.drop_column("documents", "review_notes")
    op.drop_column("documents", "review_status")
    op.drop_column("documents", "title")
    review_status.drop(op.get_bind(), checkfirst=True)
