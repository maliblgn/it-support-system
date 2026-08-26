import logging
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from math import ceil

from sqlalchemy import func, select, true
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import Notification, Ticket, TicketRating, TicketWatcher, User
from app.models.enums import (
    EmailStatus,
    NotificationType,
    TicketResolutionOutcome,
    UserRole,
)
from app.schemas.notification import NotificationPage, NotificationRead

logger = logging.getLogger(__name__)


class NotificationNotFoundError(LookupError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _send_email(notification: Notification, settings: Settings) -> None:
    if not settings.smtp_host or not settings.mail_from or not notification.email_recipient:
        raise RuntimeError("SMTP gönderimi yapılandırılmadı.")

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = notification.email_recipient
    message["Subject"] = notification.title
    message.set_content(notification.message)

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    ) as smtp:
        smtp.ehlo()
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if settings.smtp_username:
            password = (
                settings.smtp_password.get_secret_value()
                if settings.smtp_password is not None
                else ""
            )
            smtp.login(settings.smtp_username, password)
        smtp.send_message(message)


def _deliver_notification(
    notification: Notification,
    settings: Settings,
    session: Session,
) -> None:
    if (
        not settings.email_delivery_enabled
        or not notification.email_recipient
        or not settings.smtp_host
    ):
        notification.email_status = EmailStatus.SKIPPED.value
        notification.updated_at = _utc_now()
        session.commit()
        return

    notification.email_attempt_count += 1
    try:
        _send_email(notification, settings)
    except Exception as exc:  # SMTP sürücüleri farklı hata sınıfları döndürebilir.
        notification.email_status = EmailStatus.FAILED.value
        notification.email_last_error = str(exc)[:1000]
        logger.error(
            "Bildirim e-postası gönderilemedi.",
            extra={"notification_id": notification.id, "ticket_id": notification.ticket_id},
        )
    else:
        notification.email_status = EmailStatus.SENT.value
        notification.email_last_error = None
        notification.email_sent_at = _utc_now()
        logger.info(
            "Bildirim e-postası gönderildi.",
            extra={"notification_id": notification.id, "ticket_id": notification.ticket_id},
        )
    notification.updated_at = _utc_now()
    session.commit()


def notify_new_ticket(ticket: Ticket, session: Session, settings: Settings) -> None:
    active_it_users = session.scalars(
        select(User).where(User.role == UserRole.IT.value, User.is_active == true())
    ).all()
    configured_recipients = set(settings.it_notification_recipients)
    active_it_emails = {user.email for user in active_it_users}
    unmatched = configured_recipients - active_it_emails
    if unmatched:
        logger.warning(
            "Bazı IT e-posta alıcıları aktif IT hesabıyla eşleşmedi; gönderim atlandı.",
            extra={"unmatched_recipient_count": len(unmatched)},
        )

    notifications = [
        Notification(
            user_id=user.id,
            ticket_id=ticket.id,
            type=NotificationType.NEW_TICKET.value,
            title=f"Yeni ticket: {ticket.ticket_number}",
            message=(
                f"{ticket.ticket_number} numaralı '{ticket.subject}' konusu için yeni ticket "
                f"{ticket.created_at.isoformat()} UTC tarihinde oluşturuldu."
            ),
            is_read=False,
            email_recipient=(
                user.email
                if not configured_recipients or user.email in configured_recipients
                else None
            ),
            email_status=EmailStatus.PENDING.value,
            email_attempt_count=0,
        )
        for user in active_it_users
    ]
    _persist_and_deliver(notifications, session, settings, ticket.id)


def notify_ticket_resolved(ticket: Ticket, session: Session, settings: Settings) -> None:
    owner = session.get(User, ticket.user_id)
    if owner is None:
        logger.error(
            "Çözüm bildirimi için ticket sahibi bulunamadı.",
            extra={"ticket_id": ticket.id},
        )
        return
    was_resolved = ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value
    result_text = "çözüldü" if was_resolved else "çözülemedi olarak sonuçlandırıldı"
    notification = Notification(
        user_id=owner.id,
        ticket_id=ticket.id,
        type=(
            NotificationType.TICKET_RESOLVED.value
            if was_resolved
            else NotificationType.TICKET_UNRESOLVED.value
        ),
        title=(
            f"Ticket çözüldü: {ticket.ticket_number}"
            if was_resolved
            else f"Ticket çözülemedi: {ticket.ticket_number}"
        ),
        message=(
            f"{ticket.ticket_number} numaralı '{ticket.subject}' ticket'ı "
            f"{ticket.resolved_at.isoformat()} UTC tarihinde {result_text}."
        ),
        is_read=False,
        email_recipient=owner.email,
        email_status=EmailStatus.PENDING.value,
        email_attempt_count=0,
    )
    _persist_and_deliver([notification], session, settings, ticket.id)


def notify_ticket_deleted(
    ticket: Ticket,
    actor: User,
    session: Session,
    settings: Settings,
) -> None:
    recipient_ids = {ticket.user_id}
    if ticket.assigned_to is not None:
        recipient_ids.add(ticket.assigned_to)
    recipient_ids.discard(actor.id)
    recipients = session.scalars(
        select(User).where(User.id.in_(recipient_ids), User.is_active == true())
    ).all()
    notifications = [
        Notification(
            user_id=user.id,
            ticket_id=ticket.id,
            type=NotificationType.TICKET_DELETED.value,
            title=f"Ticket silindi: {ticket.ticket_number}",
            message=(
                f"{ticket.ticket_number} numaralı '{ticket.subject}' ticket'ı "
                "geri dönüşüm kutusuna taşındı."
            ),
            is_read=False,
            email_recipient=user.email,
            email_status=EmailStatus.PENDING.value,
            email_attempt_count=0,
        )
        for user in recipients
    ]
    _persist_and_deliver(notifications, session, settings, ticket.id)


def notify_ticket_rated(
    ticket: Ticket,
    rating: TicketRating,
    session: Session,
    settings: Settings,
) -> None:
    resolver = session.get(User, rating.it_user_id)
    if resolver is None or not resolver.is_active:
        return
    notification = Notification(
        user_id=resolver.id,
        ticket_id=ticket.id,
        type=NotificationType.TICKET_RATED.value,
        title=f"Ticket puanlandı: {ticket.ticket_number}",
        message=(
            f"{ticket.ticket_number} numaralı ticket için çözüm hizmetinize "
            f"5 üzerinden {rating.score} puan verildi."
        ),
        is_read=False,
        email_recipient=resolver.email,
        email_status=EmailStatus.PENDING.value,
        email_attempt_count=0,
    )
    _persist_and_deliver([notification], session, settings, ticket.id)


def notify_ticket_watchers(
    ticket: Ticket,
    actor: User,
    title: str,
    message: str,
    session: Session,
    settings: Settings,
) -> None:
    watcher_ids = session.scalars(
        select(TicketWatcher.user_id).where(
            TicketWatcher.ticket_id == ticket.id,
            TicketWatcher.user_id != actor.id,
        )
    ).all()
    if not watcher_ids:
        return
    watchers = session.scalars(
        select(User).where(User.id.in_(watcher_ids), User.is_active == true())
    ).all()
    notifications = [
        Notification(
            user_id=user.id,
            ticket_id=ticket.id,
            type=NotificationType.TICKET_UPDATED.value,
            title=title,
            message=message,
            is_read=False,
            email_recipient=user.email,
            email_status=EmailStatus.PENDING.value,
            email_attempt_count=0,
        )
        for user in watchers
    ]
    _persist_and_deliver(notifications, session, settings, ticket.id)


def _persist_and_deliver(
    notifications: list[Notification],
    session: Session,
    settings: Settings,
    ticket_id: int | None,
) -> None:
    if not notifications:
        return
    session.add_all(notifications)
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        logger.exception(
            "Sistem içi bildirimler kaydedilemedi; ticket işlemi korunuyor.",
            extra={"ticket_id": ticket_id},
        )
        return
    for notification in notifications:
        try:
            _deliver_notification(notification, settings, session)
        except SQLAlchemyError:
            session.rollback()
            logger.exception(
                "E-posta teslim durumu kaydedilemedi.",
                extra={"notification_id": notification.id, "ticket_id": ticket_id},
            )


def list_notifications(
    current_user: User,
    session: Session,
    page: int,
    page_size: int,
) -> NotificationPage:
    predicate = Notification.user_id == current_user.id
    total = session.scalar(select(func.count(Notification.id)).where(predicate)) or 0
    notifications = session.scalars(
        select(Notification)
        .where(predicate)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return NotificationPage(
        items=[NotificationRead.model_validate(item) for item in notifications],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def mark_notification_read(
    notification_id: int,
    current_user: User,
    session: Session,
) -> Notification:
    notification = session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    if notification is None:
        raise NotificationNotFoundError("Bildirim bulunamadı.")
    if not notification.is_read:
        now = _utc_now()
        notification.is_read = True
        notification.read_at = now
        notification.updated_at = now
        session.commit()
    return notification
