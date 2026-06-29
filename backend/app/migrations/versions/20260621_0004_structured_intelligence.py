"""add structured intelligence fields

Revision ID: 20260621_0004
Revises: 20260621_0003
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0004"
down_revision: str | None = "20260621_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("document_type", sa.String(length=80), nullable=True))
    op.add_column("documents", sa.Column("document_type_confidence", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("structured_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("documents", sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(op.f("ix_documents_document_type"), "documents", ["document_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_document_type"), table_name="documents")
    op.drop_column("documents", "risk_flags")
    op.drop_column("documents", "structured_fields")
    op.drop_column("documents", "document_type_confidence")
    op.drop_column("documents", "document_type")
