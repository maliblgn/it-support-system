from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DatabaseSession, EndUser
from app.schemas.rating import TicketRatingCreate, TicketRatingRead
from app.services.ratings import (
    RatingConflictError,
    RatingNotFoundError,
    get_ticket_rating,
    upsert_ticket_rating,
)

router = APIRouter()


@router.get("/{ticket_id}/rating", response_model=TicketRatingRead | None)
def get_rating(
    ticket_id: int,
    current_user: EndUser,
    session: DatabaseSession,
) -> TicketRatingRead | None:
    try:
        return get_ticket_rating(ticket_id, current_user, session)
    except RatingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{ticket_id}/rating", response_model=TicketRatingRead)
def upsert_rating(
    ticket_id: int,
    payload: TicketRatingCreate,
    current_user: EndUser,
    session: DatabaseSession,
) -> TicketRatingRead:
    try:
        return upsert_ticket_rating(ticket_id, payload, current_user, session)
    except RatingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RatingConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
