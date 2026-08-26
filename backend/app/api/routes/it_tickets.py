from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession, ItUser
from app.models.enums import TicketPriority
from app.schemas.ticket import (
    ItTicketPage,
    ItTicketRead,
    ItTicketView,
    TicketFilterOptions,
    TicketHistoryRead,
    TicketPriorityUpdate,
    TicketResolveRequest,
    TicketStatusFilter,
)
from app.services.tickets import (
    TicketConflictError,
    TicketNotFoundError,
    add_ticket_tag,
    assign_ticket_to_self,
    get_it_ticket,
    list_it_tickets,
    list_ticket_history,
    remove_ticket_tag,
    resolve_ticket,
    set_ticket_priority,
    ticket_filter_options,
    unwatch_ticket,
    watch_ticket,
)

router = APIRouter()
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
SearchText = Annotated[str | None, Query(max_length=200)]
StatusFilterQuery = Annotated[TicketStatusFilter | None, Query(alias="status")]
DepartmentText = Annotated[str | None, Query(max_length=150)]
OwnerText = Annotated[str | None, Query(max_length=200)]
PositiveInt = Annotated[int | None, Query(gt=0)]


def _not_found(exc: TicketNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: TicketConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=ItTicketPage)
def list_all(
    current_user: ItUser,
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    view: ItTicketView = ItTicketView.ALL,
    search: SearchText = None,
    status_filter: StatusFilterQuery = None,
    priority: TicketPriority | None = None,
    department: DepartmentText = None,
    owner: OwnerText = None,
    assignee_id: PositiveInt = None,
    tag_id: PositiveInt = None,
    created_from: date | None = None,
    created_to: date | None = None,
    updated_from: date | None = None,
    updated_to: date | None = None,
    resolved_from: date | None = None,
    resolved_to: date | None = None,
) -> ItTicketPage:
    return list_it_tickets(
        current_user,
        session,
        page,
        page_size,
        view,
        search,
        status_filter,
        priority,
        department,
        owner,
        assignee_id,
        tag_id,
        created_from,
        created_to,
        updated_from,
        updated_to,
        resolved_from,
        resolved_to,
    )


@router.get("/filter-options", response_model=TicketFilterOptions)
def filter_options(_: ItUser, session: DatabaseSession) -> TicketFilterOptions:
    return ticket_filter_options(session)


@router.get("/{ticket_id}", response_model=ItTicketRead)
def detail(ticket_id: int, _: ItUser, session: DatabaseSession) -> ItTicketRead:
    try:
        ticket = get_it_ticket(ticket_id, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.get("/{ticket_id}/history", response_model=list[TicketHistoryRead])
def history(ticket_id: int, _: ItUser, session: DatabaseSession) -> list[TicketHistoryRead]:
    try:
        get_it_ticket(ticket_id, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return list_ticket_history(ticket_id, session)


@router.patch("/{ticket_id}/priority", response_model=ItTicketRead)
def priority(
    ticket_id: int,
    payload: TicketPriorityUpdate,
    current_user: ItUser,
    session: DatabaseSession,
) -> ItTicketRead:
    try:
        ticket = set_ticket_priority(ticket_id, payload.priority, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    except TicketConflictError as exc:
        raise _conflict(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.post("/{ticket_id}/assign-self", response_model=ItTicketRead)
def assign_self(
    ticket_id: int,
    current_user: ItUser,
    session: DatabaseSession,
) -> ItTicketRead:
    try:
        ticket = assign_ticket_to_self(ticket_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    except TicketConflictError as exc:
        raise _conflict(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.post("/{ticket_id}/resolve", response_model=ItTicketRead)
def resolve(
    ticket_id: int,
    payload: TicketResolveRequest,
    current_user: ItUser,
    session: DatabaseSession,
) -> ItTicketRead:
    try:
        ticket = resolve_ticket(
            ticket_id,
            payload.resolution_note,
            payload.outcome,
            current_user,
            session,
        )
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    except TicketConflictError as exc:
        raise _conflict(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.post("/{ticket_id}/tags/{tag_id}", response_model=ItTicketRead)
def add_tag(
    ticket_id: int,
    tag_id: int,
    current_user: ItUser,
    session: DatabaseSession,
) -> ItTicketRead:
    try:
        ticket = add_ticket_tag(ticket_id, tag_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    except TicketConflictError as exc:
        raise _conflict(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.delete("/{ticket_id}/tags/{tag_id}", response_model=ItTicketRead)
def remove_tag(
    ticket_id: int,
    tag_id: int,
    current_user: ItUser,
    session: DatabaseSession,
) -> ItTicketRead:
    try:
        ticket = remove_ticket_tag(ticket_id, tag_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.post("/{ticket_id}/watch", response_model=ItTicketRead)
def start_watching(
    ticket_id: int, current_user: ItUser, session: DatabaseSession
) -> ItTicketRead:
    try:
        ticket = watch_ticket(ticket_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return ItTicketRead.model_validate(ticket)


@router.delete("/{ticket_id}/watch", response_model=ItTicketRead)
def stop_watching(
    ticket_id: int, current_user: ItUser, session: DatabaseSession
) -> ItTicketRead:
    try:
        ticket = unwatch_ticket(ticket_id, current_user, session)
    except TicketNotFoundError as exc:
        raise _not_found(exc) from exc
    return ItTicketRead.model_validate(ticket)
