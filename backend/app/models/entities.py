import secrets
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    Sequence,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects import mssql
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

ticket_number_seq = Sequence("ticket_number_seq", start=1, increment=1)
bigint_type = BigInteger().with_variant(Integer(), "sqlite")
utc_datetime = DateTime(timezone=False).with_variant(mssql.DATETIME2(precision=3), "mssql")
large_unicode_text = UnicodeText().with_variant(mssql.NVARCHAR(None), "mssql")
rowversion_type = mssql.TIMESTAMP().with_variant(LargeBinary(8), "sqlite")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('USER','IT','ADMIN')", name="CK_users_role"),
        Index("IX_users_department", "department"),
        Index("IX_users_role_active", "role", "is_active"),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(Unicode(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    first_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    last_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(Unicode(30))
    department: Mapped[str] = mapped_column(Unicode(150), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'USER'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    row_version: Mapped[bytes] = mapped_column(
        rowversion_type,
        nullable=False,
        server_default=FetchedValue(),
        server_onupdate=FetchedValue(),
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="user", foreign_keys="Ticket.user_id"
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="assignee", foreign_keys="Ticket.assigned_to"
    )
    resolved_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="resolver", foreign_keys="Ticket.resolved_by"
    )

    __mapper_args__ = {"version_id_col": row_version, "version_id_generator": False}


class DeletedAccount(Base):
    __tablename__ = "deleted_accounts"

    email_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    deleted_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "priority IS NULL OR priority IN ('LOW','NORMAL','HIGH','CRITICAL')",
            name="CK_tickets_priority",
        ),
        CheckConstraint(
            "(is_resolved = 0 AND resolution_note IS NULL AND resolved_at IS NULL "
            "AND resolved_by IS NULL) OR "
            "(is_resolved = 1 AND LEN(LTRIM(RTRIM(resolution_note))) > 0 "
            "AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)",
            name="CK_tickets_resolution_consistency",
        ),
        CheckConstraint(
            "is_resolved = 0 OR priority IS NOT NULL", name="CK_tickets_resolved_priority"
        ),
        CheckConstraint(
            "(is_resolved = 0 AND resolution_outcome IS NULL) OR "
            "(is_resolved = 1 AND resolution_outcome IN ('RESOLVED','UNRESOLVED'))",
            name="CK_tickets_resolution_outcome",
        ),
        CheckConstraint(
            "(deleted_at IS NULL AND deleted_by IS NULL AND deletion_reason IS NULL) OR "
            "(deleted_at IS NOT NULL AND deleted_by IS NOT NULL "
            "AND LEN(LTRIM(RTRIM(deletion_reason))) > 0)",
            name="CK_tickets_deletion_consistency",
        ),
        Index("IX_tickets_user_created", "user_id", text("created_at DESC")),
        Index("IX_tickets_pool", "is_resolved", "assigned_to", text("created_at DESC")),
        Index(
            "IX_tickets_assigned_resolved",
            "assigned_to",
            "is_resolved",
            text("created_at DESC"),
        ),
        Index("IX_tickets_department_created", "department_snapshot", text("created_at DESC")),
        Index("IX_tickets_deleted_created", "deleted_at", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    ticket_number: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    description: Mapped[str] = mapped_column(large_unicode_text, nullable=False)
    department_snapshot: Mapped[str] = mapped_column(Unicode(150), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(20))
    assigned_to: Mapped[int | None] = mapped_column(
        bigint_type, ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION")
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    resolution_outcome: Mapped[str | None] = mapped_column(String(20))
    resolution_note: Mapped[str | None] = mapped_column(large_unicode_text)
    resolved_at: Mapped[datetime | None] = mapped_column(utc_datetime)
    resolved_by: Mapped[int | None] = mapped_column(
        bigint_type, ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(utc_datetime)
    deleted_by: Mapped[int | None] = mapped_column(
        bigint_type, ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION")
    )
    deletion_reason: Mapped[str | None] = mapped_column(Unicode(500))
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    row_version: Mapped[bytes] = mapped_column(
        rowversion_type,
        nullable=False,
        server_default=FetchedValue(),
        server_onupdate=FetchedValue(),
    )

    user: Mapped[User] = relationship(back_populates="tickets", foreign_keys=[user_id])
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_tickets", foreign_keys=[assigned_to]
    )
    resolver: Mapped[User | None] = relationship(
        back_populates="resolved_tickets", foreign_keys=[resolved_by]
    )
    deleter: Mapped[User | None] = relationship(foreign_keys=[deleted_by])
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="ticket")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="ticket")
    rating: Mapped["TicketRating | None"] = relationship(
        back_populates="ticket", uselist=False
    )
    tag_links: Mapped[list["TicketTag"]] = relationship(back_populates="ticket")
    watcher_links: Mapped[list["TicketWatcher"]] = relationship(back_populates="ticket")

    @property
    def tags(self) -> list["Tag"]:
        return [link.tag for link in self.tag_links]

    @property
    def watchers(self) -> list[User]:
        return [link.user for link in self.watcher_links]

    __mapper_args__ = {"version_id_col": row_version, "version_id_generator": False}


class CannedResponse(Base):
    __tablename__ = "canned_responses"
    __table_args__ = (
        Index("IX_canned_responses_active_title", "is_active", "title"),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    title: Mapped[str] = mapped_column(Unicode(120), nullable=False)
    content: Mapped[str] = mapped_column(Unicode(2000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    created_by: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    creator: Mapped[User] = relationship(foreign_keys=[created_by])


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("name", name="UQ_tags_name"),
        Index("IX_tags_active_name", "is_active", "name"),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, server_default=text("'#2F7C91'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    created_by: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    ticket_links: Mapped[list["TicketTag"]] = relationship(back_populates="tag")


class TicketTag(Base):
    __tablename__ = "ticket_tags"
    __table_args__ = (Index("IX_ticket_tags_tag_ticket", "tag_id", "ticket_id"),)

    ticket_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("tickets.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("tags.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        primary_key=True,
    )
    added_by: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    ticket: Mapped[Ticket] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="ticket_links")
    added_by_user: Mapped[User] = relationship(foreign_keys=[added_by])


class TicketWatcher(Base):
    __tablename__ = "ticket_watchers"
    __table_args__ = (Index("IX_ticket_watchers_user_ticket", "user_id", "ticket_id"),)

    ticket_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("tickets.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    ticket: Mapped[Ticket] = relationship(back_populates="watcher_links")
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('image/png','image/jpeg','application/pdf')",
            name="CK_attachments_content_type",
        ),
        CheckConstraint(
            "file_extension IN ('.png','.jpg','.jpeg','.pdf')",
            name="CK_attachments_extension",
        ),
        CheckConstraint("file_size_bytes > 0", name="CK_attachments_size_positive"),
        Index("IX_attachments_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("tickets.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    uploaded_by: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    original_file_name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    stored_file_name: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    storage_key: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(bigint_type, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    ticket: Mapped[Ticket] = relationship(back_populates="attachments")
    uploader: Mapped[User] = relationship(foreign_keys=[uploaded_by])


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('NEW_TICKET','TICKET_UPDATED','TICKET_RESOLVED','TICKET_UNRESOLVED',"
            "'TICKET_DELETED','TICKET_RATED')",
            name="CK_notifications_type",
        ),
        CheckConstraint(
            "email_status IN ('PENDING','SENT','FAILED','SKIPPED')",
            name="CK_notifications_email_status",
        ),
        CheckConstraint("email_attempt_count >= 0", name="CK_notifications_attempt_count"),
        CheckConstraint(
            "(is_read = 0 AND read_at IS NULL) OR (is_read = 1 AND read_at IS NOT NULL)",
            name="CK_notifications_read_consistency",
        ),
        Index("IX_notifications_user_read", "user_id", "is_read", text("created_at DESC")),
        Index("IX_notifications_ticket", "ticket_id"),
        Index("IX_notifications_email_status", "email_status", "created_at"),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    ticket_id: Mapped[int | None] = mapped_column(
        bigint_type,
        ForeignKey("tickets.id", ondelete="NO ACTION", onupdate="NO ACTION"),
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    message: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    read_at: Mapped[datetime | None] = mapped_column(utc_datetime)
    email_recipient: Mapped[str | None] = mapped_column(Unicode(320))
    email_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDING'")
    )
    email_attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    email_last_error: Mapped[str | None] = mapped_column(Unicode(1000))
    email_sent_at: Mapped[datetime | None] = mapped_column(utc_datetime)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    ticket: Mapped[Ticket | None] = relationship(back_populates="notifications")


class TicketRating(Base):
    __tablename__ = "ticket_ratings"
    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 5", name="CK_ticket_ratings_score"),
        UniqueConstraint("ticket_id", name="UQ_ticket_ratings_ticket"),
        Index("IX_ticket_ratings_it_created", "it_user_id", text("created_at DESC")),
        Index("IX_ticket_ratings_user_created", "user_id", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("tickets.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    it_user_id: Mapped[int] = mapped_column(
        bigint_type,
        ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Unicode(1000))
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    ticket: Mapped[Ticket] = relationship(back_populates="rating")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    it_user: Mapped[User] = relationship(foreign_keys=[it_user_id])


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("IX_audit_events_actor_created", "actor_user_id", text("created_at DESC")),
        Index("IX_audit_events_entity", "entity_type", "entity_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(bigint_type, Identity(), primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        bigint_type, ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION")
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(bigint_type)
    details_json: Mapped[str | None] = mapped_column(Unicode(2000))
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])


def _set_sqlite_row_version(
    _mapper: object,
    connection: Connection,
    target: User | Ticket,
) -> None:
    """SQLite testleri için MSSQL ROWVERSION davranışını yaklaşık olarak taklit eder."""
    if connection.dialect.name == "sqlite":
        now = datetime.now(UTC).replace(tzinfo=None)
        target.row_version = secrets.token_bytes(8)
        if target.created_at is None:
            target.created_at = now
        target.updated_at = now


event.listen(User, "before_insert", _set_sqlite_row_version)
event.listen(User, "before_update", _set_sqlite_row_version)
event.listen(Ticket, "before_insert", _set_sqlite_row_version)
event.listen(Ticket, "before_update", _set_sqlite_row_version)
