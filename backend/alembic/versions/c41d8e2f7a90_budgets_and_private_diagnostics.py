"""budgets and private diagnostics

Revision ID: c41d8e2f7a90
Revises: 8b31f0c2a9d4
Create Date: 2026-08-09 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c41d8e2f7a90"
down_revision: str | Sequence[str] | None = "8b31f0c2a9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monthly_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("couple_id", sa.Uuid(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("limit_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name=op.f("ck_monthly_budgets_currency_length"),
        ),
        sa.CheckConstraint(
            "extract(day from month) = 1",
            name=op.f("ck_monthly_budgets_month_starts_on_first"),
        ),
        sa.CheckConstraint("limit_amount > 0", name=op.f("ck_monthly_budgets_positive_limit")),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["couple_id"], ["couples.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monthly_budgets_couple_id", "monthly_budgets", ["couple_id"])
    op.create_index(
        "ix_monthly_budgets_couple_month",
        "monthly_budgets",
        ["couple_id", "month"],
    )
    op.create_index(
        "uq_monthly_budgets_scope",
        "monthly_budgets",
        ["couple_id", "month", "category_id"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )

    op.create_table(
        "client_error_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("couple_id", sa.Uuid(), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=False),
        sa.Column("error_type", sa.String(length=100), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("stack_frames", sa.JSON(), nullable=False),
        sa.Column("screen", sa.String(length=50), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["couple_id"], ["couples.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_error_reports_user_id", "client_error_reports", ["user_id"])
    op.create_index("ix_client_error_reports_couple_id", "client_error_reports", ["couple_id"])
    op.create_index("ix_client_error_reports_fingerprint", "client_error_reports", ["fingerprint"])
    op.create_index("ix_client_error_reports_created", "client_error_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_client_error_reports_created", table_name="client_error_reports")
    op.drop_index("ix_client_error_reports_fingerprint", table_name="client_error_reports")
    op.drop_index("ix_client_error_reports_couple_id", table_name="client_error_reports")
    op.drop_index("ix_client_error_reports_user_id", table_name="client_error_reports")
    op.drop_table("client_error_reports")

    op.drop_index("uq_monthly_budgets_scope", table_name="monthly_budgets")
    op.drop_index("ix_monthly_budgets_couple_month", table_name="monthly_budgets")
    op.drop_index("ix_monthly_budgets_couple_id", table_name="monthly_budgets")
    op.drop_table("monthly_budgets")
