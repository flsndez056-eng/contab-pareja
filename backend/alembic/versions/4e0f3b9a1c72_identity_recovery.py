"""identity recovery

Revision ID: 4e0f3b9a1c72
Revises: 2777d2869229
Create Date: 2026-08-05 02:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4e0f3b9a1c72"
down_revision: str | Sequence[str] | None = "2777d2869229"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_table(
        "email_action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('verify_email', 'reset_password')",
            name=op.f("ck_email_action_tokens_valid_purpose"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_action_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_action_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_email_action_tokens_token_hash")),
    )
    op.create_index(
        "ix_email_action_tokens_active",
        "email_action_tokens",
        ["user_id", "purpose", "expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_action_tokens_user_id"),
        "email_action_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_email_action_tokens_user_id"), table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_active", table_name="email_action_tokens")
    op.drop_table("email_action_tokens")
    op.drop_column("users", "auth_version")
