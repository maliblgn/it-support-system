"""V1 başlangıç MSSQL şeması.

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mssql

revision: str = "20260821_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE SEQUENCE dbo.ticket_number_seq AS BIGINT START WITH 1 INCREMENT BY 1"
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("email", sa.Unicode(320), nullable=False),
        sa.Column("password_hash", sa.Unicode(255), nullable=False),
        sa.Column("first_name", sa.Unicode(100), nullable=False),
        sa.Column("last_name", sa.Unicode(100), nullable=False),
        sa.Column("phone", sa.Unicode(30), nullable=True),
        sa.Column("department", sa.Unicode(150), nullable=False),
        sa.Column("role", sa.String(20), server_default=sa.text("'USER'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
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
        sa.Column("row_version", mssql.TIMESTAMP(), nullable=False),
        sa.CheckConstraint("role IN ('USER','IT')", name="CK_users_role"),
        sa.PrimaryKeyConstraint("id", name="PK_users"),
        sa.UniqueConstraint("email", name="UQ_users_email"),
    )
    op.create_index("IX_users_department", "users", ["department"], unique=False)
    op.create_index("IX_users_role_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("ticket_number", sa.String(16), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("subject", sa.Unicode(200), nullable=False),
        sa.Column("description", mssql.NVARCHAR(None), nullable=False),
        sa.Column("department_snapshot", sa.Unicode(150), nullable=False),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("resolution_note", mssql.NVARCHAR(None), nullable=True),
        sa.Column("resolved_at", mssql.DATETIME2(precision=3), nullable=True),
        sa.Column("resolved_by", sa.BigInteger(), nullable=True),
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
        sa.Column("row_version", mssql.TIMESTAMP(), nullable=False),
        sa.CheckConstraint(
            "priority IS NULL OR priority IN ('LOW','NORMAL','HIGH','CRITICAL')",
            name="CK_tickets_priority",
        ),
        sa.CheckConstraint(
            "(is_resolved = 0 AND resolution_note IS NULL AND resolved_at IS NULL "
            "AND resolved_by IS NULL) OR "
            "(is_resolved = 1 AND LEN(LTRIM(RTRIM(resolution_note))) > 0 "
            "AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)",
            name="CK_tickets_resolution_consistency",
        ),
        sa.CheckConstraint(
            "is_resolved = 0 OR priority IS NOT NULL", name="CK_tickets_resolved_priority"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"], ["users.id"], name="FK_tickets_assigned_to", ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"], name="FK_tickets_resolved_by", ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="FK_tickets_user", ondelete="NO ACTION"
        ),
        sa.PrimaryKeyConstraint("id", name="PK_tickets"),
        sa.UniqueConstraint("ticket_number", name="UQ_tickets_ticket_number"),
    )
    op.create_index(
        "IX_tickets_user_created", "tickets", ["user_id", sa.text("created_at DESC")], unique=False
    )
    op.create_index(
        "IX_tickets_pool",
        "tickets",
        ["is_resolved", "assigned_to", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "IX_tickets_assigned_resolved",
        "tickets",
        ["assigned_to", "is_resolved", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "IX_tickets_department_created",
        "tickets",
        ["department_snapshot", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("original_file_name", sa.Unicode(255), nullable=False),
        sa.Column("stored_file_name", sa.String(36), nullable=False),
        sa.Column("storage_key", sa.Unicode(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_extension", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            mssql.DATETIME2(precision=3),
            server_default=sa.text("SYSUTCDATETIME()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_type IN ('image/png','image/jpeg','application/pdf')",
            name="CK_attachments_content_type",
        ),
        sa.CheckConstraint(
            "file_extension IN ('.png','.jpg','.jpeg','.pdf')",
            name="CK_attachments_extension",
        ),
        sa.CheckConstraint("file_size_bytes > 0", name="CK_attachments_size_positive"),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name="FK_attachments_ticket", ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name="FK_attachments_uploaded_by",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="PK_attachments"),
        sa.UniqueConstraint("stored_file_name", name="UQ_attachments_stored_name"),
    )
    op.create_index(
        "IX_attachments_ticket_created", "attachments", ["ticket_id", "created_at"], unique=False
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.Unicode(200), nullable=False),
        sa.Column("message", sa.Unicode(1000), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("read_at", mssql.DATETIME2(precision=3), nullable=True),
        sa.Column("email_recipient", sa.Unicode(320), nullable=True),
        sa.Column(
            "email_status", sa.String(20), server_default=sa.text("'PENDING'"), nullable=False
        ),
        sa.Column("email_attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("email_last_error", sa.Unicode(1000), nullable=True),
        sa.Column("email_sent_at", mssql.DATETIME2(precision=3), nullable=True),
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
        sa.CheckConstraint(
            "type IN ('NEW_TICKET','TICKET_RESOLVED')", name="CK_notifications_type"
        ),
        sa.CheckConstraint(
            "email_status IN ('PENDING','SENT','FAILED','SKIPPED')",
            name="CK_notifications_email_status",
        ),
        sa.CheckConstraint(
            "email_attempt_count >= 0", name="CK_notifications_attempt_count"
        ),
        sa.CheckConstraint(
            "(is_read = 0 AND read_at IS NULL) OR (is_read = 1 AND read_at IS NOT NULL)",
            name="CK_notifications_read_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="FK_notifications_ticket",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="FK_notifications_user", ondelete="NO ACTION"
        ),
        sa.PrimaryKeyConstraint("id", name="PK_notifications"),
    )
    op.create_index(
        "IX_notifications_user_read",
        "notifications",
        ["user_id", "is_read", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "IX_notifications_ticket", "notifications", ["ticket_id"], unique=False
    )
    op.create_index(
        "IX_notifications_email_status",
        "notifications",
        ["email_status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("IX_notifications_email_status", table_name="notifications")
    op.drop_index("IX_notifications_ticket", table_name="notifications")
    op.drop_index("IX_notifications_user_read", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("IX_attachments_ticket_created", table_name="attachments")
    op.drop_table("attachments")

    op.drop_index("IX_tickets_department_created", table_name="tickets")
    op.drop_index("IX_tickets_assigned_resolved", table_name="tickets")
    op.drop_index("IX_tickets_pool", table_name="tickets")
    op.drop_index("IX_tickets_user_created", table_name="tickets")
    op.drop_table("tickets")

    op.drop_index("IX_users_role_active", table_name="users")
    op.drop_index("IX_users_department", table_name="users")
    op.drop_table("users")

    op.execute("DROP SEQUENCE dbo.ticket_number_seq")
