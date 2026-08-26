import json
from datetime import UTC, datetime
from math import ceil

from sqlalchemy import delete, false, func, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.core.security import (
    account_email_fingerprint,
    hash_password,
    validate_allowed_email,
)
from app.models.entities import (
    Attachment,
    AuditEvent,
    CannedResponse,
    DeletedAccount,
    Notification,
    Tag,
    Ticket,
    TicketRating,
    TicketTag,
    TicketWatcher,
    User,
)
from app.models.enums import TicketResolutionOutcome, UserRole
from app.schemas.admin import AdminDashboardRead, AdminUserPage, AuditEventPage, AuditEventRead
from app.schemas.user import UserRead
from app.services.audit import record_audit_event
from app.services.auth import _is_email_unique_violation


class AdminResourceNotFoundError(LookupError):
    pass


class AdminConflictError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _managed_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None or user.role == UserRole.ADMIN.value:
        raise AdminResourceNotFoundError("Kullanıcı bulunamadı.")
    return user


def _ensure_demo_account_mutable(user: User, settings: Settings) -> None:
    if settings.is_demo_account_protected(user.email):
        raise AdminConflictError(
            "Bu hesap ortak demonun çalışması için korunmaktadır ve değiştirilemez."
        )


def list_users(
    session: Session,
    page: int,
    page_size: int,
    search: str | None,
    role: UserRole | None,
    is_active: bool | None,
) -> AdminUserPage:
    query = select(User).where(User.role != UserRole.ADMIN.value)
    if role is not None:
        if role == UserRole.ADMIN:
            return AdminUserPage(items=[], total=0, page=page, page_size=page_size, pages=0)
        query = query.where(User.role == role.value)
    if is_active is not None:
        query = query.where(User.is_active == (true() if is_active else false()))

    normalized_search = (search or "").strip()
    if normalized_search:
        query = query.where(
            or_(
                User.email.contains(normalized_search, autoescape=True),
                User.first_name.contains(normalized_search, autoescape=True),
                User.last_name.contains(normalized_search, autoescape=True),
                User.department.contains(normalized_search, autoescape=True),
            )
        )

    total = session.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    users = session.scalars(
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminUserPage(
        items=[UserRead.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def create_it_user(
    *,
    email: str,
    temporary_password: str,
    first_name: str,
    last_name: str,
    phone: str | None,
    department: str,
    actor: User,
    session: Session,
    settings: Settings,
) -> User:
    allowed_email = validate_allowed_email(email, settings.allowed_email_domains)
    user = User(
        email=allowed_email,
        password_hash=hash_password(temporary_password, settings),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        department=department,
        role=UserRole.IT.value,
        is_active=True,
        must_change_password=True,
    )
    session.add(user)
    try:
        session.flush()
        record_audit_event(
            session,
            actor,
            "IT_USER_CREATED",
            "USER",
            user.id,
            {"email": user.email, "role": user.role},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if _is_email_unique_violation(exc):
            raise AdminConflictError("Bu e-posta adresi zaten kayıtlı.") from exc
        raise
    session.refresh(user)
    return user


def update_managed_user(
    user_id: int,
    changes: dict[str, object],
    actor: User,
    session: Session,
    settings: Settings,
) -> User:
    user = _managed_user(session, user_id)
    _ensure_demo_account_mutable(user, settings)
    for field, value in changes.items():
        setattr(user, field, value)
    user.updated_at = _utc_now()
    record_audit_event(
        session,
        actor,
        "USER_PROFILE_UPDATED",
        "USER",
        user.id,
        {"changed_fields": sorted(changes)},
    )
    session.commit()
    session.refresh(user)
    return user


def set_managed_user_status(
    user_id: int,
    is_active: bool,
    reason: str,
    actor: User,
    session: Session,
    settings: Settings,
) -> User:
    user = _managed_user(session, user_id)
    _ensure_demo_account_mutable(user, settings)
    if user.is_active == is_active:
        raise AdminConflictError(
            "Kullanıcı zaten aktif." if is_active else "Kullanıcı zaten pasif."
        )
    user.is_active = is_active
    user.updated_at = _utc_now()
    record_audit_event(
        session,
        actor,
        "USER_ACTIVATED" if is_active else "USER_DEACTIVATED",
        "USER",
        user.id,
        {"reason": reason},
    )
    session.commit()
    session.refresh(user)
    return user


def reset_managed_user_password(
    user_id: int,
    temporary_password: str,
    reason: str,
    actor: User,
    session: Session,
    settings: Settings,
) -> User:
    user = _managed_user(session, user_id)
    _ensure_demo_account_mutable(user, settings)
    user.password_hash = hash_password(temporary_password, settings)
    user.must_change_password = True
    user.updated_at = _utc_now()
    record_audit_event(
        session,
        actor,
        "USER_TEMPORARY_PASSWORD_SET",
        "USER",
        user.id,
        {"reason": reason},
    )
    session.commit()
    session.refresh(user)
    return user


def permanently_delete_managed_user(
    user_id: int,
    confirmation_email: str,
    reason: str,
    actor: User,
    session: Session,
    settings: Settings,
) -> None:
    user = _managed_user(session, user_id)
    _ensure_demo_account_mutable(user, settings)
    if user.email != confirmation_email:
        raise AdminConflictError("Onay e-postası silinecek kullanıcıyla eşleşmiyor.")

    history_checks = {
        "talep sahibi": select(func.count(Ticket.id)).where(Ticket.user_id == user.id),
        "atanan IT çalışanı": select(func.count(Ticket.id)).where(Ticket.assigned_to == user.id),
        "çözümleyen IT çalışanı": select(func.count(Ticket.id)).where(
            Ticket.resolved_by == user.id
        ),
        "talep silen kullanıcı": select(func.count(Ticket.id)).where(Ticket.deleted_by == user.id),
        "dosya yükleyen kullanıcı": select(func.count(Attachment.id)).where(
            Attachment.uploaded_by == user.id
        ),
        "puan veren kullanıcı": select(func.count(TicketRating.id)).where(
            TicketRating.user_id == user.id
        ),
        "puanlanan IT çalışanı": select(func.count(TicketRating.id)).where(
            TicketRating.it_user_id == user.id
        ),
        "ticket takipçisi": select(func.count(TicketWatcher.user_id)).where(
            TicketWatcher.user_id == user.id
        ),
        "etiket ekleyen kullanıcı": select(func.count(TicketTag.added_by)).where(
            TicketTag.added_by == user.id
        ),
        "etiket oluşturan kullanıcı": select(func.count(Tag.id)).where(
            Tag.created_by == user.id
        ),
        "hazır cevap oluşturan kullanıcı": select(func.count(CannedResponse.id)).where(
            CannedResponse.created_by == user.id
        ),
    }
    blocking_history = [
        label for label, query in history_checks.items() if (session.scalar(query) or 0) > 0
    ]
    if blocking_history:
        labels = ", ".join(blocking_history)
        raise AdminConflictError(
            "Bu kullanıcı iş geçmişine bağlı olduğu için kalıcı olarak silinemez "
            f"({labels}). Kayıt bütünlüğünü korumak için hesabı pasifleştirin."
        )

    # İş geçmişi olmayan hesaba ait kişisel bildirim ve denetim izleri hesapla kaldırılır.
    session.execute(delete(Notification).where(Notification.user_id == user.id))
    session.execute(
        delete(AuditEvent).where(
            or_(
                AuditEvent.actor_user_id == user.id,
                (AuditEvent.entity_type == "USER") & (AuditEvent.entity_id == user.id),
            )
        )
    )
    deleted_user_id = user.id
    deleted_role = user.role
    email_hash = account_email_fingerprint(user.email, settings)
    deleted_account = session.get(DeletedAccount, email_hash)
    if deleted_account is None:
        session.add(DeletedAccount(email_hash=email_hash))
    else:
        deleted_account.deleted_at = _utc_now()
    session.delete(user)
    record_audit_event(
        session,
        actor,
        "USER_PERMANENTLY_DELETED",
        "USER",
        deleted_user_id,
        {"role": deleted_role, "reason": reason},
    )
    session.commit()


def dashboard_summary(session: Session) -> AdminDashboardRead:
    total_users = session.scalar(
        select(func.count(User.id)).where(User.role != UserRole.ADMIN.value)
    ) or 0
    active_users = session.scalar(
        select(func.count(User.id)).where(
            User.role != UserRole.ADMIN.value,
            User.is_active == true(),
        )
    ) or 0
    it_users = session.scalar(
        select(func.count(User.id)).where(User.role == UserRole.IT.value)
    ) or 0
    open_tickets = session.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.is_resolved == false(),
            Ticket.deleted_at.is_(None),
        )
    ) or 0
    deleted_tickets = session.scalar(
        select(func.count(Ticket.id)).where(Ticket.deleted_at.is_not(None))
    ) or 0
    unrated_resolved_tickets = session.scalar(
        select(func.count(Ticket.id))
        .outerjoin(TicketRating, TicketRating.ticket_id == Ticket.id)
        .where(
            Ticket.is_resolved == true(),
            Ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value,
            Ticket.deleted_at.is_(None),
            TicketRating.id.is_(None),
        )
    ) or 0
    return AdminDashboardRead(
        total_users=total_users,
        active_users=active_users,
        it_users=it_users,
        open_tickets=open_tickets,
        deleted_tickets=deleted_tickets,
        unrated_resolved_tickets=unrated_resolved_tickets,
    )


def list_audit_events(
    session: Session,
    page: int,
    page_size: int,
    action: str | None,
) -> AuditEventPage:
    query = select(AuditEvent).options(joinedload(AuditEvent.actor))
    normalized_action = (action or "").strip()
    if normalized_action:
        query = query.where(AuditEvent.action == normalized_action)
    total = session.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    events = session.scalars(
        query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for event in events:
        try:
            details = json.loads(event.details_json) if event.details_json else {}
        except json.JSONDecodeError:
            details = {"raw": event.details_json or ""}
        actor_name = (
            f"{event.actor.first_name} {event.actor.last_name}"
            if event.actor is not None
            else None
        )
        items.append(
            AuditEventRead(
                id=event.id,
                actor_user_id=event.actor_user_id,
                actor_name=actor_name,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                details=details,
                created_at=event.created_at,
            )
        )
    return AuditEventPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )
