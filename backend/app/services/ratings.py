from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models.entities import Ticket, TicketRating, User
from app.models.enums import TicketResolutionOutcome
from app.schemas.rating import TicketRatingCreate, TicketRatingRead
from app.services.audit import record_audit_event
from app.services.notifications import notify_ticket_rated

RATING_WINDOW = timedelta(days=7)


class RatingNotFoundError(LookupError):
    pass


class RatingConflictError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _rating_ticket(ticket_id: int, current_user: User, session: Session) -> Ticket:
    ticket = session.scalar(
        select(Ticket)
        .options(joinedload(Ticket.rating), joinedload(Ticket.resolver))
        .where(
            Ticket.id == ticket_id,
            Ticket.user_id == current_user.id,
            Ticket.deleted_at.is_(None),
        )
    )
    if ticket is None:
        raise RatingNotFoundError("Ticket bulunamadı.")
    return ticket


def _editable_until(ticket: Ticket) -> datetime:
    if ticket.resolved_at is None:
        raise RatingConflictError("Yalnızca çözülmüş ticket puanlanabilir.")
    return ticket.resolved_at + RATING_WINDOW


def _rating_read(ticket: Ticket, rating: TicketRating) -> TicketRatingRead:
    resolver = rating.it_user if rating.it_user is not None else ticket.resolver
    if resolver is None:
        raise RatingConflictError("Ticket çözüm personeli bulunamadı.")
    return TicketRatingRead(
        id=rating.id,
        ticket_id=rating.ticket_id,
        user_id=rating.user_id,
        it_user_id=rating.it_user_id,
        it_user_name=f"{resolver.first_name} {resolver.last_name}",
        score=rating.score,
        comment=rating.comment,
        editable_until=_editable_until(ticket),
        created_at=rating.created_at,
        updated_at=rating.updated_at,
    )


def get_ticket_rating(
    ticket_id: int, current_user: User, session: Session
) -> TicketRatingRead | None:
    ticket = _rating_ticket(ticket_id, current_user, session)
    if ticket.rating is None:
        return None
    return _rating_read(ticket, ticket.rating)


def upsert_ticket_rating(
    ticket_id: int,
    payload: TicketRatingCreate,
    current_user: User,
    session: Session,
) -> TicketRatingRead:
    ticket = _rating_ticket(ticket_id, current_user, session)
    if (
        not ticket.is_resolved
        or ticket.resolution_outcome != TicketResolutionOutcome.RESOLVED.value
        or ticket.resolved_by is None
    ):
        raise RatingConflictError("Yalnızca çözülmüş ticket puanlanabilir.")
    now = _utc_now()
    if now > _editable_until(ticket):
        raise RatingConflictError("Ticket için 7 günlük puanlama süresi dolmuş.")
    rating = ticket.rating
    action = "TICKET_RATING_CREATED"
    if rating is None:
        rating = TicketRating(
            ticket_id=ticket.id,
            user_id=current_user.id,
            it_user_id=ticket.resolved_by,
            score=payload.score,
            comment=payload.comment,
        )
        session.add(rating)
    else:
        rating.score = payload.score
        rating.comment = payload.comment
        rating.updated_at = now
        action = "TICKET_RATING_UPDATED"

    session.flush()
    record_audit_event(
        session,
        current_user,
        action,
        "TICKET_RATING",
        rating.id,
        {"score": rating.score, "ticket_id": ticket.id},
    )
    session.commit()
    session.refresh(rating)
    rating.it_user = ticket.resolver
    notify_ticket_rated(ticket, rating, session, get_settings())
    return _rating_read(ticket, rating)
