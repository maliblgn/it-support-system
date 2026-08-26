"""Ticket operasyon geliştirmeleri için ek tabloları oluştur.

Revision ID: 20260825_0005
Revises: 20260825_0004
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mssql

revision: str = "20260825_0005"
down_revision: str | None = "20260825_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utc_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        mssql.DATETIME2(precision=3),
        server_default=sa.text("SYSUTCDATETIME()"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_index(
        "IX_tickets_operations",
        "tickets",
        ["deleted_at", "is_resolved", "priority", "assigned_to", sa.text("updated_at DESC")],
        unique=False,
    )

    op.create_table(
        "canned_responses",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("title", sa.Unicode(120), nullable=False),
        sa.Column("content", sa.Unicode(2000), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        _utc_column("created_at"),
        _utc_column("updated_at"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="FK_canned_responses_creator", ondelete="NO ACTION"
        ),
        sa.PrimaryKeyConstraint("id", name="PK_canned_responses"),
    )
    op.create_index(
        "IX_canned_responses_active_title",
        "canned_responses",
        ["is_active", "title"],
        unique=False,
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.Unicode(50), nullable=False),
        sa.Column("color", sa.String(7), server_default=sa.text("'#2F7C91'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        _utc_column("created_at"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="FK_tags_creator", ondelete="NO ACTION"
        ),
        sa.PrimaryKeyConstraint("id", name="PK_tags"),
        sa.UniqueConstraint("name", name="UQ_tags_name"),
    )
    op.create_index("IX_tags_active_name", "tags", ["is_active", "name"], unique=False)

    op.create_table(
        "ticket_tags",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("added_by", sa.BigInteger(), nullable=False),
        _utc_column("created_at"),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name="FK_ticket_tags_ticket", ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name="FK_ticket_tags_tag", ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["added_by"], ["users.id"], name="FK_ticket_tags_added_by", ondelete="NO ACTION"
        ),
        sa.PrimaryKeyConstraint("ticket_id", "tag_id", name="PK_ticket_tags"),
    )
    op.create_index(
        "IX_ticket_tags_tag_ticket", "ticket_tags", ["tag_id", "ticket_id"], unique=False
    )

    op.create_table(
        "ticket_watchers",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        _utc_column("created_at"),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name="FK_ticket_watchers_ticket", ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="FK_ticket_watchers_user", ondelete="NO ACTION"
        ),
        sa.PrimaryKeyConstraint("ticket_id", "user_id", name="PK_ticket_watchers"),
    )
    op.create_index(
        "IX_ticket_watchers_user_ticket",
        "ticket_watchers",
        ["user_id", "ticket_id"],
        unique=False,
    )

    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_UPDATED','TICKET_RESOLVED','TICKET_UNRESOLVED',"
        "'TICKET_DELETED','TICKET_RATED')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM notifications WHERE type = 'TICKET_UPDATED'")
    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED','TICKET_UNRESOLVED',"
        "'TICKET_DELETED','TICKET_RATED')",
    )
    op.drop_index("IX_ticket_watchers_user_ticket", table_name="ticket_watchers")
    op.drop_table("ticket_watchers")
    op.drop_index("IX_ticket_tags_tag_ticket", table_name="ticket_tags")
    op.drop_table("ticket_tags")
    op.drop_index("IX_tags_active_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("IX_canned_responses_active_title", table_name="canned_responses")
    op.drop_table("canned_responses")
    op.drop_index("IX_tickets_operations", table_name="tickets")
