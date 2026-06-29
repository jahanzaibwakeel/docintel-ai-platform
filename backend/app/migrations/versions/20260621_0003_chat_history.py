"""add document chat history

Revision ID: 20260621_0003
Revises: 20260621_0002
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0003"
down_revision: str | None = "20260621_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    message_role = postgresql.ENUM("user", "assistant", name="messagerole", create_type=False)
    message_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "document_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_messages_document_id"), "document_messages", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_messages_id"), "document_messages", ["id"], unique=False)
    op.create_index(op.f("ix_document_messages_role"), "document_messages", ["role"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_messages_role"), table_name="document_messages")
    op.drop_index(op.f("ix_document_messages_id"), table_name="document_messages")
    op.drop_index(op.f("ix_document_messages_document_id"), table_name="document_messages")
    op.drop_table("document_messages")
    sa.Enum(name="messagerole").drop(op.get_bind(), checkfirst=True)
