"""Ödül sistemini ve eski bildirimlerini kaldır.

Revision ID: 20260825_0004
Revises: 20260825_0003
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mssql

revision: str = "20260825_0004"
down_revision: str | None = "20260825_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM notifications WHERE type = 'REWARD_FINALIZED'")
    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED','TICKET_UNRESOLVED',"
        "'TICKET_DELETED','TICKET_RATED')",
    )
    op.drop_index("IX_reward_periods_status_start", table_name="reward_periods")
    op.drop_table("reward_periods")


def downgrade() -> None:
    op.create_table(
        "reward_periods",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("reward_title", sa.Unicode(200), nullable=False),
        sa.Column(
            "minimum_ratings", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "status", sa.String(20), server_default=sa.text("'DRAFT'"), nullable=False
        ),
        sa.Column("winner_it_user_id", sa.BigInteger(), nullable=True),
        sa.Column("winner_total_score", sa.Integer(), nullable=True),
        sa.Column("winner_average_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("winner_rating_count", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("finalized_by", sa.BigInteger(), nullable=True),
        sa.Column("finalized_at", mssql.DATETIME2(precision=3), nullable=True),
        sa.Column(
            "created_at",
            mssql.DATETIME2(precision=3),
            server_default=sa.text("SYSUTCDATETIME()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mssql.DATETIME2(precision=3),
            server_default=sa.text("SYSUTCDATETIME()"),
            nullable=False,
        ),
        sa.CheckConstraint("period_start <= period_end", name="CK_reward_periods_dates"),
        sa.CheckConstraint(
            "minimum_ratings >= 1", name="CK_reward_periods_minimum_ratings"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','FINALIZED')", name="CK_reward_periods_status"
        ),
        sa.CheckConstraint(
            "(status = 'DRAFT' AND winner_it_user_id IS NULL "
            "AND finalized_by IS NULL AND finalized_at IS NULL) OR "
            "(status = 'FINALIZED' AND winner_it_user_id IS NOT NULL "
            "AND winner_total_score IS NOT NULL AND winner_average_score IS NOT NULL "
            "AND winner_rating_count IS NOT NULL AND finalized_by IS NOT NULL "
            "AND finalized_at IS NOT NULL)",
            name="CK_reward_periods_finalization",
        ),
        sa.ForeignKeyConstraint(
            ["winner_it_user_id"],
            ["users.id"],
            name="FK_reward_periods_winner",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="FK_reward_periods_created_by",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["finalized_by"],
            ["users.id"],
            name="FK_reward_periods_finalized_by",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="PK_reward_periods"),
        sa.UniqueConstraint("period_start", "period_end", name="UQ_reward_periods_dates"),
    )
    op.create_index(
        "IX_reward_periods_status_start",
        "reward_periods",
        ["status", sa.text("period_start DESC")],
        unique=False,
    )
    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED','TICKET_UNRESOLVED',"
        "'TICKET_DELETED','TICKET_RATED','REWARD_FINALIZED')",
    )
