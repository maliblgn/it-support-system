import json
import logging
from datetime import UTC, date, datetime, time, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from sqlalchemy import Select, false, func, or_, select, text, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.orm.exc import StaleDataError

from app.core.config import get_settings
from app.models.entities import AuditEvent, Tag, Ticket, TicketTag, TicketWatcher, User
from app.models.enums import TicketPriority, TicketResolutionOutcome, UserRole
from app.schemas.operations import TagCreate
from app.schemas.ticket import (
    AdminTicketPage,
    AdminTicketRead,
    AdminTicketState,
    ItTicketPage,
    ItTicketRead,
    ItTicketView,
    TicketCreate,
    TicketFilterAssignee,
    TicketFilterOptions,
    TicketHistoryRead,
    TicketPage,
    TicketRead,
    TicketStatusFilter,
    TicketTagRead,
    TicketUpdate,
)
from app.services.audit import record_audit_event
from app.services.notifications import (
    notify_new_ticket,
    notify_ticket_deleted,
    notify_ticket_resolved,
    notify_ticket_watchers,
)

logger = logging.getLogger(__name__)
ISTANBUL = ZoneInfo("Europe/Istanbul")


class TicketNotFoundError(LookupError):
    pass


class TicketConflictError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _local_day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=ISTANBUL).astimezone(UTC).replace(tzinfo=None)


def _apply_status_filter(
    query: Select[tuple[Ticket]], status_filter: TicketStatusFilter | None
) -> Select[tuple[Ticket]]:
    if status_filter == TicketStatusFilter.OPEN:
        return query.where(Ticket.is_resolved == false())
    if status_filter == TicketStatusFilter.RESOLVED:
        return query.where(
            Ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value
        )
    if status_filter == TicketStatusFilter.UNRESOLVED:
        return query.where(
            Ticket.resolution_outcome == TicketResolutionOutcome.UNRESOLVED.value
        )
    return query


def _apply_date_range(
    query: Select[tuple[Ticket]],
    column: object,
    date_from: date | None,
    date_to: date | None,
) -> Select[tuple[Ticket]]:
    if date_from is not None:
        query = query.where(column >= _local_day_start(date_from))
    if date_to is not None:
        query = query.where(column < _local_day_start(date_to + timedelta(days=1)))
    return query


def _ticket_query() -> Select[tuple[Ticket]]:
    return select(Ticket).options(
        joinedload(Ticket.user),
        joinedload(Ticket.assignee),
        selectinload(Ticket.attachments),
        selectinload(Ticket.tag_links).joinedload(TicketTag.tag),
        selectinload(Ticket.watcher_links).joinedload(TicketWatcher.user),
    )


def _get_ticket(
    session: Session, ticket_id: int, *, include_deleted: bool = False
) -> Ticket | None:
    query = _ticket_query().execution_options(populate_existing=True).where(Ticket.id == ticket_id)
    if not include_deleted:
        query = query.where(Ticket.deleted_at.is_(None))
    return session.scalar(query)


def _page_result(
    session: Session,
    query: Select[tuple[Ticket]],
    page: int,
    page_size: int,
) -> TicketPage:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = session.scalar(count_query) or 0
    tickets = session.scalars(
        query.order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return TicketPage(
        items=[TicketRead.model_validate(ticket) for ticket in tickets],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def _it_page_result(
    session: Session,
    query: Select[tuple[Ticket]],
    page: int,
    page_size: int,
) -> ItTicketPage:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = session.scalar(count_query) or 0
    tickets = session.scalars(
        query.order_by(Ticket.updated_at.desc(), Ticket.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ItTicketPage(
        items=[ItTicketRead.model_validate(ticket) for ticket in tickets],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def _admin_page_result(
    session: Session,
    query: Select[tuple[Ticket]],
    page: int,
    page_size: int,
) -> AdminTicketPage:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = session.scalar(count_query) or 0
    tickets = session.scalars(
        query.order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminTicketPage(
        items=[AdminTicketRead.model_validate(ticket) for ticket in tickets],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def _next_ticket_number(session: Session) -> str:
    if session.bind is not None and session.bind.dialect.name == "mssql":
        sequence_value = session.scalar(text("SELECT NEXT VALUE FOR dbo.ticket_number_seq"))
    else:
        sequence_value = session.scalar(select(func.coalesce(func.max(Ticket.id), 0) + 1))
    if sequence_value is None or sequence_value < 1:
        raise RuntimeError("Ticket numarası üretilemedi.")
    return f"IT-{sequence_value:06d}"


def create_ticket(payload: TicketCreate, current_user: User, session: Session) -> Ticket:
    ticket = Ticket(
        ticket_number=_next_ticket_number(session),
        user_id=current_user.id,
        subject=payload.subject,
        description=payload.description,
        department_snapshot=current_user.department,
        priority=None,
        assigned_to=None,
        is_resolved=False,
        user=current_user,
    )
    session.add(ticket)
    session.flush()
    record_audit_event(
        session,
        current_user,
        "TICKET_CREATED",
        "TICKET",
        ticket.id,
        {"ticket_number": ticket.ticket_number, "subject": ticket.subject},
    )
    session.commit()
    logger.info(
        "Ticket oluşturuldu.",
        extra={
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "user_id": current_user.id,
        },
    )
    notify_new_ticket(ticket, session, get_settings())
    return ticket


def list_user_tickets(
    current_user: User,
    session: Session,
    page: int,
    page_size: int,
    search: str | None = None,
    status_filter: TicketStatusFilter | None = None,
    priority: TicketPriority | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    updated_from: date | None = None,
    updated_to: date | None = None,
) -> TicketPage:
    query = _ticket_query().where(
        Ticket.user_id == current_user.id,
        Ticket.deleted_at.is_(None),
    )
    normalized_search = (search or "").strip()
    if normalized_search:
        query = query.where(
            or_(
                Ticket.ticket_number.contains(normalized_search, autoescape=True),
                Ticket.subject.contains(normalized_search, autoescape=True),
                Ticket.description.contains(normalized_search, autoescape=True),
                Ticket.resolution_note.contains(normalized_search, autoescape=True),
            )
        )
    query = _apply_status_filter(query, status_filter)
    if priority is not None:
        query = query.where(Ticket.priority == priority.value)
    query = _apply_date_range(query, Ticket.created_at, created_from, created_to)
    query = _apply_date_range(query, Ticket.updated_at, updated_from, updated_to)
    return _page_result(session, query, page, page_size)


def get_user_ticket(ticket_id: int, current_user: User, session: Session) -> Ticket:
    ticket = session.scalar(
        _ticket_query().where(
            Ticket.id == ticket_id,
            Ticket.user_id == current_user.id,
            Ticket.deleted_at.is_(None),
        )
    )
    if ticket is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return ticket


def update_user_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    current_user: User,
    session: Session,
) -> Ticket:
    ticket = get_user_ticket(ticket_id, current_user, session)
    if ticket.is_resolved:
        raise TicketConflictError("Çözülmüş ticket düzenlenemez.")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(ticket, field, value)
    ticket.updated_at = _utc_now()
    record_audit_event(
        session,
        current_user,
        "TICKET_UPDATED",
        "TICKET",
        ticket.id,
        {"changed_fields": sorted(changes)},
    )
    try:
        session.commit()
    except StaleDataError as exc:
        session.rollback()
        raise TicketConflictError("Ticket başka bir işlem tarafından güncellendi.") from exc
    logger.info(
        "Ticket kullanıcı tarafından güncellendi.",
        extra={"ticket_id": ticket.id, "user_id": current_user.id},
    )
    notify_ticket_watchers(
        ticket,
        current_user,
        f"Ticket güncellendi: {ticket.ticket_number}",
        f"{ticket.ticket_number} numaralı ticket kullanıcı tarafından güncellendi.",
        session,
        get_settings(),
    )
    return ticket


def list_it_tickets(
    current_user: User,
    session: Session,
    page: int,
    page_size: int,
    view: ItTicketView,
    search: str | None,
    status_filter: TicketStatusFilter | None = None,
    priority: TicketPriority | None = None,
    department: str | None = None,
    owner: str | None = None,
    assignee_id: int | None = None,
    tag_id: int | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    updated_from: date | None = None,
    updated_to: date | None = None,
    resolved_from: date | None = None,
    resolved_to: date | None = None,
) -> ItTicketPage:
    query = _ticket_query().join(Ticket.user).where(Ticket.deleted_at.is_(None))
    if view == ItTicketView.UNASSIGNED:
        query = query.where(Ticket.assigned_to.is_(None), Ticket.is_resolved == false())
    elif view == ItTicketView.MINE:
        query = query.where(Ticket.assigned_to == current_user.id, Ticket.is_resolved == false())
    elif view == ItTicketView.RESOLVED:
        query = query.where(Ticket.is_resolved == true())

    normalized_search = (search or "").strip()
    if normalized_search:
        query = query.where(
            or_(
                Ticket.ticket_number.contains(normalized_search, autoescape=True),
                Ticket.subject.contains(normalized_search, autoescape=True),
                Ticket.description.contains(normalized_search, autoescape=True),
                Ticket.resolution_note.contains(normalized_search, autoescape=True),
                Ticket.department_snapshot.contains(normalized_search, autoescape=True),
                User.email.contains(normalized_search, autoescape=True),
                User.first_name.contains(normalized_search, autoescape=True),
                User.last_name.contains(normalized_search, autoescape=True),
            )
        )
    query = _apply_status_filter(query, status_filter)
    if priority is not None:
        query = query.where(Ticket.priority == priority.value)
    normalized_department = (department or "").strip()
    if normalized_department:
        query = query.where(Ticket.department_snapshot == normalized_department)
    normalized_owner = (owner or "").strip()
    if normalized_owner:
        query = query.where(
            or_(
                User.email.contains(normalized_owner, autoescape=True),
                User.first_name.contains(normalized_owner, autoescape=True),
                User.last_name.contains(normalized_owner, autoescape=True),
            )
        )
    if assignee_id is not None:
        query = query.where(Ticket.assigned_to == assignee_id)
    if tag_id is not None:
        query = query.join(TicketTag, TicketTag.ticket_id == Ticket.id).where(
            TicketTag.tag_id == tag_id
        )
    query = _apply_date_range(query, Ticket.created_at, created_from, created_to)
    query = _apply_date_range(query, Ticket.updated_at, updated_from, updated_to)
    query = _apply_date_range(query, Ticket.resolved_at, resolved_from, resolved_to)
    return _it_page_result(session, query, page, page_size)


def get_it_ticket(ticket_id: int, session: Session) -> Ticket:
    ticket = _get_ticket(session, ticket_id)
    if ticket is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return ticket


def get_admin_ticket(ticket_id: int, session: Session) -> Ticket:
    ticket = _get_ticket(session, ticket_id, include_deleted=True)
    if ticket is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return ticket


def set_ticket_priority(
    ticket_id: int,
    priority: TicketPriority,
    current_user: User,
    session: Session,
) -> Ticket:
    ticket = get_it_ticket(ticket_id, session)
    if ticket.is_resolved:
        raise TicketConflictError("Çözülmüş ticket'ın önceliği değiştirilemez.")
    previous_priority = ticket.priority
    ticket.priority = priority.value
    ticket.updated_at = _utc_now()
    record_audit_event(
        session,
        current_user,
        "TICKET_PRIORITY_CHANGED",
        "TICKET",
        ticket.id,
        {"from": previous_priority, "to": priority.value},
    )
    try:
        session.commit()
    except StaleDataError as exc:
        session.rollback()
        raise TicketConflictError("Ticket başka bir işlem tarafından güncellendi.") from exc
    logger.info(
        "Ticket önceliği güncellendi.",
        extra={"ticket_id": ticket.id, "priority": priority.value},
    )
    notify_ticket_watchers(
        ticket,
        current_user,
        f"Öncelik güncellendi: {ticket.ticket_number}",
        f"{ticket.ticket_number} numaralı ticket önceliği {priority.value} olarak güncellendi.",
        session,
        get_settings(),
    )
    return ticket


def assign_ticket_to_self(ticket_id: int, current_user: User, session: Session) -> Ticket:
    now = _utc_now()
    result = session.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.assigned_to.is_(None),
            Ticket.is_resolved == false(),
            Ticket.deleted_at.is_(None),
        )
        .values(assigned_to=current_user.id, updated_at=now)
    )
    if result.rowcount == 1:
        record_audit_event(
            session,
            current_user,
            "TICKET_ASSIGNED_SELF",
            "TICKET",
            ticket_id,
            {"assigned_it_user_id": current_user.id},
        )
        session.commit()
        logger.info(
            "Ticket IT kullanıcısı tarafından üzerine alındı.",
            extra={"ticket_id": ticket_id, "it_user_id": current_user.id},
        )
        ticket = _get_ticket(session, ticket_id)
        if ticket is None:
            raise TicketNotFoundError("Ticket bulunamadı.")
        notify_ticket_watchers(
            ticket,
            current_user,
            f"Ticket atandı: {ticket.ticket_number}",
            f"{ticket.ticket_number} numaralı ticket {current_user.first_name} "
            f"{current_user.last_name} tarafından üzerine alındı.",
            session,
            get_settings(),
        )
        return ticket

    session.rollback()
    ticket = _get_ticket(session, ticket_id)
    if ticket is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    if ticket.is_resolved:
        raise TicketConflictError("Çözülmüş ticket üzerine alınamaz.")
    raise TicketConflictError("Ticket başka bir IT kullanıcısı tarafından üzerine alındı.")


def assign_ticket_by_admin(
    ticket_id: int,
    it_user_id: int,
    current_user: User,
    session: Session,
) -> Ticket:
    assignee = session.get(User, it_user_id)
    if (
        assignee is None
        or assignee.role != UserRole.IT.value
        or not assignee.is_active
    ):
        raise TicketConflictError("Talep yalnızca aktif bir IT çalışanına atanabilir.")

    ticket = _get_ticket(session, ticket_id, include_deleted=True)
    if ticket is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    if ticket.deleted_at is not None:
        raise TicketConflictError("Silinmiş ticket bir IT çalışanına atanamaz.")
    if ticket.is_resolved:
        raise TicketConflictError("Çözülmüş ticket yeniden atanamaz.")
    if ticket.assigned_to == assignee.id:
        raise TicketConflictError("Ticket zaten seçilen IT çalışanına atanmış.")

    previous_assignee_id = ticket.assigned_to
    ticket.assignee = assignee
    ticket.updated_at = _utc_now()
    record_audit_event(
        session,
        current_user,
        "TICKET_ASSIGNED_BY_ADMIN",
        "TICKET",
        ticket.id,
        {
            "ticket_number": ticket.ticket_number,
            "previous_assignee_id": previous_assignee_id,
            "assigned_it_user_id": assignee.id,
        },
    )
    try:
        session.commit()
    except StaleDataError as exc:
        session.rollback()
        raise TicketConflictError("Ticket başka bir işlem tarafından güncellendi.") from exc
    logger.info(
        "Ticket admin tarafından IT çalışanına atandı.",
        extra={
            "ticket_id": ticket.id,
            "admin_user_id": current_user.id,
            "it_user_id": assignee.id,
            "previous_it_user_id": previous_assignee_id,
        },
    )
    notify_ticket_watchers(
        ticket,
        current_user,
        f"Ticket ataması güncellendi: {ticket.ticket_number}",
        f"{ticket.ticket_number} numaralı ticket {assignee.first_name} "
        f"{assignee.last_name} adlı IT çalışanına atandı.",
        session,
        get_settings(),
    )
    return ticket


def resolve_ticket(
    ticket_id: int,
    resolution_note: str,
    outcome: TicketResolutionOutcome,
    current_user: User,
    session: Session,
) -> Ticket:
    ticket = get_it_ticket(ticket_id, session)
    if ticket.is_resolved:
        raise TicketConflictError("Ticket zaten çözülmüş.")
    if ticket.assigned_to != current_user.id:
        raise TicketConflictError("Ticket çözülmeden önce üzerinize alınmalıdır.")
    if ticket.priority is None:
        raise TicketConflictError("Ticket çözülmeden önce öncelik belirlenmelidir.")

    now = _utc_now()
    ticket.is_resolved = True
    ticket.resolution_outcome = outcome.value
    ticket.resolution_note = resolution_note
    ticket.resolved_at = now
    ticket.resolved_by = current_user.id
    ticket.updated_at = now
    record_audit_event(
        session,
        current_user,
        (
            "TICKET_RESOLVED"
            if outcome == TicketResolutionOutcome.RESOLVED
            else "TICKET_MARKED_UNRESOLVED"
        ),
        "TICKET",
        ticket.id,
        {"outcome": outcome.value, "resolution_note_length": len(resolution_note)},
    )
    try:
        session.commit()
    except StaleDataError as exc:
        session.rollback()
        raise TicketConflictError("Ticket başka bir işlem tarafından güncellendi.") from exc
    logger.info(
        "Ticket sonuçlandırıldı.",
        extra={
            "ticket_id": ticket.id,
            "it_user_id": current_user.id,
            "resolution_outcome": outcome.value,
        },
    )
    notify_ticket_resolved(ticket, session, get_settings())
    notify_ticket_watchers(
        ticket,
        current_user,
        f"Ticket sonuçlandırıldı: {ticket.ticket_number}",
        f"{ticket.ticket_number} numaralı ticket {outcome.value} sonucuyla kapatıldı.",
        session,
        get_settings(),
    )
    return ticket


def delete_user_ticket(
    ticket_id: int,
    reason: str,
    current_user: User,
    session: Session,
) -> Ticket:
    ticket = get_user_ticket(ticket_id, current_user, session)
    if ticket.is_resolved:
        raise TicketConflictError("Çözülmüş ticket kullanıcı tarafından silinemez.")
    return _soft_delete_ticket(ticket, reason, current_user, session)


def delete_admin_ticket(
    ticket_id: int,
    reason: str,
    current_user: User,
    session: Session,
) -> Ticket:
    ticket = _get_ticket(session, ticket_id)
    if ticket is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return _soft_delete_ticket(ticket, reason, current_user, session)


def _soft_delete_ticket(
    ticket: Ticket,
    reason: str,
    current_user: User,
    session: Session,
) -> Ticket:
    now = _utc_now()
    ticket.deleted_at = now
    ticket.deleted_by = current_user.id
    ticket.deletion_reason = reason
    ticket.updated_at = now
    record_audit_event(
        session,
        current_user,
        "TICKET_DELETED",
        "TICKET",
        ticket.id,
        {"reason": reason, "ticket_number": ticket.ticket_number},
    )
    try:
        session.commit()
    except StaleDataError as exc:
        session.rollback()
        raise TicketConflictError("Ticket başka bir işlem tarafından güncellendi.") from exc
    logger.info(
        "Ticket soft-delete ile silindi.",
        extra={"ticket_id": ticket.id, "user_id": current_user.id},
    )
    notify_ticket_deleted(ticket, current_user, session, get_settings())
    return ticket


def restore_admin_ticket(
    ticket_id: int,
    current_user: User,
    session: Session,
) -> Ticket:
    ticket = _get_ticket(session, ticket_id, include_deleted=True)
    if ticket is None or ticket.deleted_at is None:
        raise TicketNotFoundError("Silinmiş ticket bulunamadı.")
    previous_reason = ticket.deletion_reason
    ticket.deleted_at = None
    ticket.deleted_by = None
    ticket.deletion_reason = None
    ticket.updated_at = _utc_now()
    record_audit_event(
        session,
        current_user,
        "TICKET_RESTORED",
        "TICKET",
        ticket.id,
        {"previous_deletion_reason": previous_reason or ""},
    )
    try:
        session.commit()
    except StaleDataError as exc:
        session.rollback()
        raise TicketConflictError("Ticket başka bir işlem tarafından güncellendi.") from exc
    logger.info(
        "Ticket geri dönüşüm kutusundan geri yüklendi.",
        extra={"ticket_id": ticket.id, "user_id": current_user.id},
    )
    return ticket


def ticket_filter_options(session: Session) -> TicketFilterOptions:
    departments = session.scalars(
        select(Ticket.department_snapshot)
        .where(Ticket.deleted_at.is_(None))
        .distinct()
        .order_by(Ticket.department_snapshot)
    ).all()
    assignees = session.scalars(
        select(User)
        .where(
            User.role == UserRole.IT.value,
            User.is_active == true(),
        )
        .order_by(User.first_name, User.last_name, User.id)
    ).all()
    tags = session.scalars(
        select(Tag).where(Tag.is_active == true()).order_by(Tag.name, Tag.id)
    ).all()
    return TicketFilterOptions(
        departments=list(departments),
        assignees=[
            TicketFilterAssignee(id=user.id, name=f"{user.first_name} {user.last_name}")
            for user in assignees
        ],
        tags=[TicketTagRead.model_validate(tag) for tag in tags],
    )


def list_tags(session: Session) -> list[Tag]:
    return list(
        session.scalars(
            select(Tag).where(Tag.is_active == true()).order_by(Tag.name, Tag.id)
        ).all()
    )


def create_tag(payload: TagCreate, current_user: User, session: Session) -> Tag:
    tag = Tag(
        name=payload.name,
        color=payload.color.upper(),
        is_active=True,
        created_by=current_user.id,
    )
    session.add(tag)
    try:
        session.flush()
        record_audit_event(
            session,
            current_user,
            "TAG_CREATED",
            "TAG",
            tag.id,
            {"name": tag.name},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise TicketConflictError("Bu etiket zaten mevcut.") from exc
    session.refresh(tag)
    return tag


def add_ticket_tag(
    ticket_id: int, tag_id: int, current_user: User, session: Session
) -> Ticket:
    ticket = get_it_ticket(ticket_id, session)
    tag = session.scalar(select(Tag).where(Tag.id == tag_id, Tag.is_active == true()))
    if tag is None:
        raise TicketNotFoundError("Etiket bulunamadı.")
    if session.get(TicketTag, (ticket_id, tag_id)) is not None:
        raise TicketConflictError("Etiket zaten ticket üzerinde mevcut.")
    session.add(TicketTag(ticket_id=ticket_id, tag_id=tag_id, added_by=current_user.id))
    ticket.updated_at = _utc_now()
    record_audit_event(
        session,
        current_user,
        "TICKET_TAG_ADDED",
        "TICKET",
        ticket.id,
        {"tag_id": tag.id, "tag_name": tag.name},
    )
    session.commit()
    refreshed = _get_ticket(session, ticket_id)
    if refreshed is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return refreshed


def remove_ticket_tag(
    ticket_id: int, tag_id: int, current_user: User, session: Session
) -> Ticket:
    ticket = get_it_ticket(ticket_id, session)
    link = session.get(TicketTag, (ticket_id, tag_id))
    if link is None:
        raise TicketNotFoundError("Ticket etiketi bulunamadı.")
    tag_name = link.tag.name
    session.delete(link)
    ticket.updated_at = _utc_now()
    record_audit_event(
        session,
        current_user,
        "TICKET_TAG_REMOVED",
        "TICKET",
        ticket.id,
        {"tag_id": tag_id, "tag_name": tag_name},
    )
    session.commit()
    refreshed = _get_ticket(session, ticket_id)
    if refreshed is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return refreshed


def watch_ticket(ticket_id: int, current_user: User, session: Session) -> Ticket:
    ticket = get_it_ticket(ticket_id, session)
    if session.get(TicketWatcher, (ticket_id, current_user.id)) is None:
        session.add(TicketWatcher(ticket_id=ticket_id, user_id=current_user.id))
        record_audit_event(
            session,
            current_user,
            "TICKET_WATCH_STARTED",
            "TICKET",
            ticket.id,
        )
        session.commit()
    refreshed = _get_ticket(session, ticket_id)
    if refreshed is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return refreshed


def unwatch_ticket(ticket_id: int, current_user: User, session: Session) -> Ticket:
    ticket = get_it_ticket(ticket_id, session)
    link = session.get(TicketWatcher, (ticket_id, current_user.id))
    if link is not None:
        session.delete(link)
        record_audit_event(
            session,
            current_user,
            "TICKET_WATCH_STOPPED",
            "TICKET",
            ticket.id,
        )
        session.commit()
    refreshed = _get_ticket(session, ticket_id)
    if refreshed is None:
        raise TicketNotFoundError("Ticket bulunamadı.")
    return refreshed


def list_ticket_history(ticket_id: int, session: Session) -> list[TicketHistoryRead]:
    events = session.scalars(
        select(AuditEvent)
        .options(joinedload(AuditEvent.actor))
        .where(AuditEvent.entity_type == "TICKET", AuditEvent.entity_id == ticket_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
    ).all()
    items: list[TicketHistoryRead] = []
    for event in events:
        try:
            details = json.loads(event.details_json) if event.details_json else {}
        except json.JSONDecodeError:
            details = {}
        items.append(
            TicketHistoryRead(
                id=event.id,
                action=event.action,
                actor_user_id=event.actor_user_id,
                actor_name=(
                    f"{event.actor.first_name} {event.actor.last_name}"
                    if event.actor is not None
                    else None
                ),
                details=details,
                created_at=event.created_at,
            )
        )
    return items


def list_admin_tickets(
    session: Session,
    page: int,
    page_size: int,
    state: AdminTicketState,
    search: str | None,
) -> AdminTicketPage:
    query = _ticket_query().join(Ticket.user)
    if state == AdminTicketState.ACTIVE:
        query = query.where(Ticket.deleted_at.is_(None))
    elif state == AdminTicketState.DELETED:
        query = query.where(Ticket.deleted_at.is_not(None))

    normalized_search = (search or "").strip()
    if normalized_search:
        query = query.where(
            or_(
                Ticket.ticket_number.contains(normalized_search, autoescape=True),
                Ticket.subject.contains(normalized_search, autoescape=True),
                Ticket.department_snapshot.contains(normalized_search, autoescape=True),
                User.email.contains(normalized_search, autoescape=True),
                User.first_name.contains(normalized_search, autoescape=True),
                User.last_name.contains(normalized_search, autoescape=True),
            )
        )
    return _admin_page_result(session, query, page, page_size)
