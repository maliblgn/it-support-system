"""Silinen hesap izi ve ticket sonuç durumu.

Revision ID: 20260825_0003
Revises: 20260824_0002
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mssql

revision: str = "20260825_0003"
down_revision: str | None = "20260824_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deleted_accounts",
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column(
            "deleted_at",
            mssql.DATETIME2(precision=3),
            server_default=sa.text("SYSUTCDATETIME()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("email_hash", name="PK_deleted_accounts"),
    )

    op.add_column(
        "tickets",
        sa.Column("resolution_outcome", sa.String(20), nullable=True),
    )
    op.execute(
        "UPDATE tickets SET resolution_outcome = 'RESOLVED' WHERE is_resolved = 1"
    )
    op.create_check_constraint(
        "CK_tickets_resolution_outcome",
        "tickets",
        "(is_resolved = 0 AND resolution_outcome IS NULL) OR "
        "(is_resolved = 1 AND resolution_outcome IN ('RESOLVED','UNRESOLVED'))",
    )
    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED','TICKET_UNRESOLVED',"
        "'TICKET_DELETED','TICKET_RATED','REWARD_FINALIZED')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM notifications WHERE type = 'TICKET_UNRESOLVED'")
    op.drop_constraint("CK_notifications_type", "notifications", type_="check")
    op.create_check_constraint(
        "CK_notifications_type",
        "notifications",
        "type IN ('NEW_TICKET','TICKET_RESOLVED','TICKET_DELETED',"
        "'TICKET_RATED','REWARD_FINALIZED')",
    )
    op.drop_constraint("CK_tickets_resolution_outcome", "tickets", type_="check")
    op.drop_column("tickets", "resolution_outcome")
    op.drop_table("deleted_accounts")
