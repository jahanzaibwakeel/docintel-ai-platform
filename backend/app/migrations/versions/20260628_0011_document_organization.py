"""add document organization fields

Revision ID: 20260628_0011
Revises: 20260627_0010
Create Date: 2026-06-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260628_0011"
down_revision: str | None = "20260627_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("documents", sa.Column("favorite", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_index(op.f("ix_documents_favorite"), "documents", ["favorite"], unique=False)
    op.create_index("ix_documents_tags_gin", "documents", ["tags"], unique=False, postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_documents_tags_gin", table_name="documents")
    op.drop_index(op.f("ix_documents_favorite"), table_name="documents")
    op.drop_column("documents", "favorite")
    op.drop_column("documents", "tags")
