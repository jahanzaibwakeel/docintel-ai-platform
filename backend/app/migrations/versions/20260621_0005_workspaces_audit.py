"""add workspaces and audit logs

Revision ID: 20260621_0005
Revises: 20260621_0004
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0005"
down_revision: str | None = "20260621_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    workspace_role = postgresql.ENUM("owner", "admin", "member", "viewer", name="workspacerole", create_type=False)
    workspace_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspaces_id"), "workspaces", ["id"], unique=False)

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", workspace_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index(op.f("ix_workspace_members_id"), "workspace_members", ["id"], unique=False)
    op.create_index(op.f("ix_workspace_members_role"), "workspace_members", ["role"], unique=False)
    op.create_index(op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"], unique=False)
    op.create_index(op.f("ix_workspace_members_workspace_id"), "workspace_members", ["workspace_id"], unique=False)

    op.add_column("documents", sa.Column("workspace_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_documents_workspace_id", "documents", "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE")
    op.create_index(op.f("ix_documents_workspace_id"), "documents", ["workspace_id"], unique=False)

    op.execute(
        """
        INSERT INTO workspaces (name)
        SELECT full_name || '''s Workspace #' || id
        FROM users
        ORDER BY id
        """
    )
    op.execute(
        """
        INSERT INTO workspace_members (workspace_id, user_id, role)
        SELECT w.id, u.id, 'owner'
        FROM users u
        JOIN workspaces w ON w.name = u.full_name || '''s Workspace #' || u.id
        """
    )
    op.execute(
        """
        UPDATE documents d
        SET workspace_id = wm.workspace_id
        FROM workspace_members wm
        WHERE wm.user_id = d.owner_id
        """
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_document_id"), "audit_logs", ["document_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_workspace_id"), "audit_logs", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_workspace_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_document_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_documents_workspace_id"), table_name="documents")
    op.drop_constraint("fk_documents_workspace_id", "documents", type_="foreignkey")
    op.drop_column("documents", "workspace_id")
    op.drop_index(op.f("ix_workspace_members_workspace_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_user_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_role"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_id"), table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index(op.f("ix_workspaces_id"), table_name="workspaces")
    op.drop_table("workspaces")
    sa.Enum(name="workspacerole").drop(op.get_bind(), checkfirst=True)
