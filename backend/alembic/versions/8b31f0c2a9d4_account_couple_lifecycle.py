"""account and couple lifecycle

Revision ID: 8b31f0c2a9d4
Revises: 4e0f3b9a1c72
Create Date: 2026-08-08 16:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8b31f0c2a9d4"
down_revision: str | Sequence[str] | None = "4e0f3b9a1c72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("couples", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("couples", sa.Column("ended_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_couples_ended_by_user_id_users"),
        "couples",
        "users",
        ["ended_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_couples_ended_at", "couples", ["ended_at"], unique=False)

    op.add_column(
        "couple_members",
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_index(op.f("ix_couple_members_user_id"), table_name="couple_members")
    op.create_index(
        op.f("ix_couple_members_user_id"),
        "couple_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_couple_members_active_user",
        "couple_members",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("left_at IS NULL"),
    )
    op.create_index(
        "ix_couple_members_user_history",
        "couple_members",
        ["user_id", "left_at"],
        unique=False,
    )

    op.add_column("invitations", sa.Column("token_hash", sa.String(length=64), nullable=True))
    op.create_unique_constraint(
        op.f("uq_invitations_token_hash"),
        "invitations",
        ["token_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_invitations_token_hash"), "invitations", type_="unique")
    op.drop_column("invitations", "token_hash")

    op.drop_index("ix_couple_members_user_history", table_name="couple_members")
    op.drop_index("uq_couple_members_active_user", table_name="couple_members")
    op.drop_index(op.f("ix_couple_members_user_id"), table_name="couple_members")
    op.execute(sa.text("DELETE FROM couple_members WHERE left_at IS NOT NULL"))
    op.create_index(
        op.f("ix_couple_members_user_id"),
        "couple_members",
        ["user_id"],
        unique=True,
    )
    op.drop_column("couple_members", "left_at")

    op.drop_index("ix_couples_ended_at", table_name="couples")
    op.drop_constraint(
        op.f("fk_couples_ended_by_user_id_users"),
        "couples",
        type_="foreignkey",
    )
    op.drop_column("couples", "ended_by_user_id")
    op.drop_column("couples", "ended_at")
    op.drop_column("users", "deleted_at")
