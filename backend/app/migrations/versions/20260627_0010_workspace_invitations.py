"""add workspace invitations

Revision ID: 20260627_0010
Revises: 20260627_0009
Create Date: 2026-06-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260627_0010"
down_revision: str | None = "20260627_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    workspace_role = postgresql.ENUM("owner", "admin", "member", "viewer", name="workspacerole", create_type=False)
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", workspace_role, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_invitations_id"), "workspace_invitations", ["id"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_workspace_id"), "workspace_invitations", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_email"), "workspace_invitations", ["email"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_role"), "workspace_invitations", ["role"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_token_hash"), "workspace_invitations", ["token_hash"], unique=True)
    op.create_index(op.f("ix_workspace_invitations_invited_by_id"), "workspace_invitations", ["invited_by_id"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_expires_at"), "workspace_invitations", ["expires_at"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_accepted_at"), "workspace_invitations", ["accepted_at"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_revoked_at"), "workspace_invitations", ["revoked_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workspace_invitations_revoked_at"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_accepted_at"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_expires_at"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_invited_by_id"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_token_hash"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_role"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_email"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_workspace_id"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_id"), table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
