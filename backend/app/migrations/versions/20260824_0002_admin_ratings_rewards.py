"""V2 admin, soft delete, puanlama ve ödül şeması.

Revision ID: 20260824_0002
Revises: 20260821_0001
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mssql

revision: str = "20260824_0002"
down_revision: str | None = "20260821_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("CK_users_role", "users", type_="check")
    op.create_check_constraint(
        "CK_users_role", "users", "role IN ('USER','IT','ADMIN')"
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )

    op.add_column(
        "tickets", sa.Column("deleted_at", mssql.DATETIME2(precision=3), nullable=True)
    )
    op.add_column("tickets", sa.Column("deleted_by", sa.BigInteger(), nullable=True))
    op.add_column(
        "tickets", sa.Column("deletion_reason", sa.Unicode(500), nullable=True)
    )
    op.create_foreign_key(
        "FK_tickets_deleted_by",
        "tickets",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="NO ACTION",
    )
    op.create_check_constraint(
        "CK_tickets_deletion_consistency",
        "tickets",
        "(deleted_at IS NULL AND deleted_by IS NULL AND deletion_reason IS NULL) OR "
        "(deleted_at IS NOT NULL AND deleted_by IS NOT NULL "
        "AND LEN(LTRIM(RTRIM(deletion_reason))) > 0)",
    )
    op.create_index(
        "IX_tickets_deleted_created",
        "tickets",
        ["deleted_at", sa.text("created_at DESC")],
        unique=False,
    )

    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED','TICKET_DELETED',"
        "'TICKET_RATED','REWARD_FINALIZED')",
    )
    op.alter_column(
        "notifications",
        "ticket_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )

    op.create_table(
        "ticket_ratings",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("it_user_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Unicode(1000), nullable=True),
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
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="CK_ticket_ratings_score"),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="FK_ticket_ratings_ticket",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="FK_ticket_ratings_user",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["it_user_id"],
            ["users.id"],
            name="FK_ticket_ratings_it_user",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="PK_ticket_ratings"),
        sa.UniqueConstraint("ticket_id", name="UQ_ticket_ratings_ticket"),
    )
    op.create_index(
        "IX_ticket_ratings_it_created",
        "ticket_ratings",
        ["it_user_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "IX_ticket_ratings_user_created",
        "ticket_ratings",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )

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
            "status",
            sa.String(20),
            server_default=sa.text("'DRAFT'"),
            nullable=False,
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
        sa.UniqueConstraint(
            "period_start", "period_end", name="UQ_reward_periods_dates"
        ),
    )
    op.create_index(
        "IX_reward_periods_status_start",
        "reward_periods",
        ["status", sa.text("period_start DESC")],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("details_json", sa.Unicode(2000), nullable=True),
        sa.Column(
            "created_at",
            mssql.DATETIME2(precision=3),
            server_default=sa.text("SYSUTCDATETIME()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="FK_audit_events_actor",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="PK_audit_events"),
    )
    op.create_index(
        "IX_audit_events_actor_created",
        "audit_events",
        ["actor_user_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "IX_audit_events_entity",
        "audit_events",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("IX_audit_events_entity", table_name="audit_events")
    op.drop_index("IX_audit_events_actor_created", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("IX_reward_periods_status_start", table_name="reward_periods")
    op.drop_table("reward_periods")

    op.drop_index("IX_ticket_ratings_user_created", table_name="ticket_ratings")
    op.drop_index("IX_ticket_ratings_it_created", table_name="ticket_ratings")
    op.drop_table("ticket_ratings")

    op.execute("DELETE FROM notifications WHERE ticket_id IS NULL")
    op.alter_column(
        "notifications",
        "ticket_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )

    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED')",
    )

    op.drop_index("IX_tickets_deleted_created", table_name="tickets")
    op.drop_constraint("CK_tickets_deletion_consistency", "tickets", type_="check")
    op.drop_constraint("FK_tickets_deleted_by", "tickets", type_="foreignkey")
    op.drop_column("tickets", "deletion_reason")
    op.drop_column("tickets", "deleted_by")
    op.drop_column("tickets", "deleted_at")

    op.drop_column("users", "must_change_password", mssql_drop_default=True)
    op.drop_constraint("CK_users_role", "users", type_="check")
    op.create_check_constraint("CK_users_role", "users", "role IN ('USER','IT')")
