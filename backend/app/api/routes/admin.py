from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import AdminUser, DatabaseSession, SettingsDependency
from app.models.enums import UserRole
from app.schemas.admin import (
    AdminDashboardRead,
    AdminItUserCreate,
    AdminTemporaryPasswordReset,
    AdminTicketAssignRequest,
    AdminUserDeleteRequest,
    AdminUserPage,
    AdminUserStatusUpdate,
    AdminUserUpdate,
    AuditEventPage,
    TicketDeleteRequest,
)
from app.schemas.ticket import (
    AdminTicketPage,
    AdminTicketRead,
    AdminTicketState,
    TicketHistoryRead,
)
from app.schemas.user import UserRead
from app.services.admin import (
    AdminConflictError,
    AdminResourceNotFoundError,
    create_it_user,
    dashboard_summary,
    list_audit_events,
    list_users,
    permanently_delete_managed_user,
    reset_managed_user_password,
    set_managed_user_status,
    update_managed_user,
)
from app.services.tickets import (
    TicketConflictError,
    TicketNotFoundError,
    assign_ticket_by_admin,
    delete_admin_ticket,
    get_admin_ticket,
    list_admin_tickets,
    list_ticket_history,
    restore_admin_ticket,
)

router = APIRouter()
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
SearchText = Annotated[str | None, Query(max_length=200)]
ActionText = Annotated[str | None, Query(max_length=80)]


def _not_found(exc: AdminResourceNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: AdminConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/dashboard", response_model=AdminDashboardRead)
def dashboard(_: AdminUser, session: DatabaseSession) -> AdminDashboardRead:
    return dashboard_summary(session)


@router.get("/users", response_model=AdminUserPage)
def users(
    _: AdminUser,
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    search: SearchText = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> AdminUserPage:
    return list_users(session, page, page_size, search, role, is_active)


@router.post("/users/it", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_it(
    payload: AdminItUserCreate,
    current_user: AdminUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = create_it_user(
            **payload.model_dump(),
            actor=current_user,
            session=session,
            settings=settings,
        )
    except AdminConflictError as exc:
        raise _conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    current_user: AdminUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = update_managed_user(
            user_id,
            payload.model_dump(exclude_unset=True),
            current_user,
            session,
            settings,
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except AdminConflictError as exc:
        raise _conflict(exc) from exc
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    current_user: AdminUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = set_managed_user_status(
            user_id, payload.is_active, payload.reason, current_user, session, settings
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except AdminConflictError as exc:
        raise _conflict(exc) from exc
    return UserRead.model_validate(user)


@router.post("/users/{user_id}/temporary-password", response_model=UserRead)
def reset_temporary_password(
    user_id: int,
    payload: AdminTemporaryPasswordReset,
    current_user: AdminUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = reset_managed_user_password(
            user_id,
            payload.temporary_password,
            payload.reason,
            current_user,
            session,
            settings,
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except AdminConflictError as exc:
        raise _conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_user(
    user_id: int,
    payload: AdminUserDeleteRequest,
    current_user: AdminUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> None:
    try:
        permanently_delete_managed_user(
            user_id,
            payload.confirmation_email,
            payload.reason,
            current_user,
            session,
            settings,
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except AdminConflictError as exc:
        raise _conflict(exc) from exc


@router.get("/audit-events", response_model=AuditEventPage)
def audit_events(
    _: AdminUser,
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 50,
    action: ActionText = None,
) -> AuditEventPage:
    return list_audit_events(session, page, page_size, action)


@router.get("/tickets", response_model=AdminTicketPage)
def tickets(
    _: AdminUser,
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    state: AdminTicketState = AdminTicketState.ACTIVE,
    search: SearchText = None,
) -> AdminTicketPage:
    return list_admin_tickets(session, page, page_size, state, search)


@router.get("/tickets/{ticket_id}", response_model=AdminTicketRead)
def ticket_detail(
    ticket_id: int,
    _: AdminUser,
    session: DatabaseSession,
) -> AdminTicketRead:
    try:
        ticket = get_admin_ticket(ticket_id, session)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminTicketRead.model_validate(ticket)


@router.get("/tickets/{ticket_id}/history", response_model=list[TicketHistoryRead])
def ticket_history(
    ticket_id: int,
    _: AdminUser,
    session: DatabaseSession,
) -> list[TicketHistoryRead]:
    try:
        get_admin_ticket(ticket_id, session)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return list_ticket_history(ticket_id, session)


@router.patch("/tickets/{ticket_id}/assignee", response_model=AdminTicketRead)
def assign_ticket(
    ticket_id: int,
    payload: AdminTicketAssignRequest,
    current_user: AdminUser,
    session: DatabaseSession,
) -> AdminTicketRead:
    try:
        ticket = assign_ticket_by_admin(
            ticket_id,
            payload.it_user_id,
            current_user,
            session,
        )
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TicketConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminTicketRead.model_validate(ticket)


@router.delete("/tickets/{ticket_id}", response_model=AdminTicketRead)
def delete_ticket(
    ticket_id: int,
    payload: TicketDeleteRequest,
    current_user: AdminUser,
    session: DatabaseSession,
) -> AdminTicketRead:
    try:
        ticket = delete_admin_ticket(ticket_id, payload.reason, current_user, session)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TicketConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminTicketRead.model_validate(ticket)


@router.post("/tickets/{ticket_id}/restore", response_model=AdminTicketRead)
def restore_ticket(
    ticket_id: int,
    current_user: AdminUser,
    session: DatabaseSession,
) -> AdminTicketRead:
    try:
        ticket = restore_admin_ticket(ticket_id, current_user, session)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TicketConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminTicketRead.model_validate(ticket)
