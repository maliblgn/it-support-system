from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession, EndUser
from app.models.enums import TicketPriority
from app.schemas.admin import TicketDeleteRequest
from app.schemas.ticket import (
    TicketCreate,
    TicketHistoryRead,
    TicketPage,
    TicketRead,
    TicketStatusFilter,
    TicketUpdate,
)
from app.services.tickets import (
    TicketConflictError,
    TicketNotFoundError,
    create_ticket,
    delete_user_ticket,
    get_user_ticket,
    list_ticket_history,
    list_user_tickets,
    update_user_ticket,
)

router = APIRouter()
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
SearchText = Annotated[str | None, Query(max_length=200)]
StatusFilterQuery = Annotated[TicketStatusFilter | None, Query(alias="status")]


def _not_found(exc: TicketNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: TicketConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: TicketCreate,
    current_user: EndUser,
    session: DatabaseSession,
) -> TicketRead:
    ticket = create_ticket(payload, current_user, session)
    return TicketRead.model_validate(ticket)


@router.get("", response_model=TicketPage)
def list_own(
    current_user: EndUser,
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    search: SearchText = None,
    status_filter: StatusFilterQuery = None,
    priority: TicketPriority | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    updated_from: date | None = None,
    updated_to: date | None = None,
) -> TicketPage:
    return list_user_tickets(
        current_user,
        session,
        page,
        page_size,
        search,
        status_filter,
        priority,
        created_from,
        created_to,
        updated_from,
        updated_to,
    )


@router.get("/{ticket_id}", response_model=TicketRead)
def detail(
    ticket_id: int,
    current_user: EndUser,
    session: DatabaseSession,
) -> TicketRead:
    try:
        ticket = get_user_ticket(ticket_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return TicketRead.model_validate(ticket)


@router.get("/{ticket_id}/history", response_model=list[TicketHistoryRead])
def history(
    ticket_id: int,
    current_user: EndUser,
    session: DatabaseSession,
) -> list[TicketHistoryRead]:
    try:
        get_user_ticket(ticket_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return list_ticket_history(ticket_id, session)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_own(
    ticket_id: int,
    payload: TicketUpdate,
    current_user: EndUser,
    session: DatabaseSession,
) -> TicketRead:
    try:
        ticket = update_user_ticket(ticket_id, payload, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    except TicketConflictError as exc:
        raise _conflict(exc) from exc
    return TicketRead.model_validate(ticket)


@router.delete("/{ticket_id}", response_model=TicketRead)
def delete_own(
    ticket_id: int,
    payload: TicketDeleteRequest,
    current_user: EndUser,
    session: DatabaseSession,
) -> TicketRead:
    try:
        ticket = delete_user_ticket(ticket_id, payload.reason, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    except TicketConflictError as exc:
        raise _conflict(exc) from exc
    return TicketRead.model_validate(ticket)
