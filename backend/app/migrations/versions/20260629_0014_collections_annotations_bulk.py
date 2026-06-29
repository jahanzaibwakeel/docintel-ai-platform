"""add collections annotations and bulk metadata

Revision ID: 20260629_0014
Revises: 20260628_0013
Create Date: 2026-06-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260629_0014"
down_revision: str | None = "20260628_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_collections_id"), "document_collections", ["id"], unique=False)
    op.create_index(op.f("ix_document_collections_workspace_id"), "document_collections", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_document_collections_created_by_id"), "document_collections", ["created_by_id"], unique=False)
    op.add_column("documents", sa.Column("collection_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_documents_collection_id_document_collections", "documents", "document_collections", ["collection_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_documents_collection_id"), "documents", ["collection_id"], unique=False)
    op.create_table(
        "document_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_annotations_id"), "document_annotations", ["id"], unique=False)
    op.create_index(op.f("ix_document_annotations_document_id"), "document_annotations", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_annotations_user_id"), "document_annotations", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_annotations_user_id"), table_name="document_annotations")
    op.drop_index(op.f("ix_document_annotations_document_id"), table_name="document_annotations")
    op.drop_index(op.f("ix_document_annotations_id"), table_name="document_annotations")
    op.drop_table("document_annotations")
    op.drop_index(op.f("ix_documents_collection_id"), table_name="documents")
    op.drop_constraint("fk_documents_collection_id_document_collections", "documents", type_="foreignkey")
    op.drop_column("documents", "collection_id")
    op.drop_index(op.f("ix_document_collections_created_by_id"), table_name="document_collections")
    op.drop_index(op.f("ix_document_collections_workspace_id"), table_name="document_collections")
    op.drop_index(op.f("ix_document_collections_id"), table_name="document_collections")
    op.drop_table("document_collections")
