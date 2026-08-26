from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AdminUser, DatabaseSession, ItOrAdminUser, ItUser
from app.schemas.operations import (
    CannedResponseCreate,
    CannedResponseRead,
    CannedResponseUpdate,
    TagCreate,
)
from app.schemas.ticket import TicketTagRead
from app.services.operations import (
    OperationResourceNotFoundError,
    create_canned_response,
    delete_canned_response,
    list_canned_responses,
    update_canned_response,
)
from app.services.tickets import TicketConflictError, create_tag, list_tags

router = APIRouter()


@router.get("/it/tags", response_model=list[TicketTagRead])
def list_ticket_tags(_: ItOrAdminUser, session: DatabaseSession) -> list[TicketTagRead]:
    return [TicketTagRead.model_validate(item) for item in list_tags(session)]


@router.post("/it/tags", response_model=TicketTagRead, status_code=status.HTTP_201_CREATED)
def create_ticket_tag(
    payload: TagCreate,
    current_user: ItOrAdminUser,
    session: DatabaseSession,
) -> TicketTagRead:
    try:
        tag = create_tag(payload, current_user, session)
    except TicketConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TicketTagRead.model_validate(tag)


@router.get("/it/canned-responses", response_model=list[CannedResponseRead])
def list_for_it(_: ItUser, session: DatabaseSession) -> list[CannedResponseRead]:
    return [CannedResponseRead.model_validate(item) for item in list_canned_responses(session)]


@router.get("/admin/canned-responses", response_model=list[CannedResponseRead])
def list_for_admin(_: AdminUser, session: DatabaseSession) -> list[CannedResponseRead]:
    return [
        CannedResponseRead.model_validate(item)
        for item in list_canned_responses(session, include_inactive=True)
    ]


@router.post(
    "/admin/canned-responses",
    response_model=CannedResponseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_for_admin(
    payload: CannedResponseCreate,
    current_user: AdminUser,
    session: DatabaseSession,
) -> CannedResponseRead:
    return CannedResponseRead.model_validate(
        create_canned_response(payload, current_user, session)
    )


@router.patch("/admin/canned-responses/{response_id}", response_model=CannedResponseRead)
def update_for_admin(
    response_id: int,
    payload: CannedResponseUpdate,
    current_user: AdminUser,
    session: DatabaseSession,
) -> CannedResponseRead:
    try:
        response = update_canned_response(response_id, payload, current_user, session)
    except OperationResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CannedResponseRead.model_validate(response)


@router.delete(
    "/admin/canned-responses/{response_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_for_admin(
    response_id: int,
    current_user: AdminUser,
    session: DatabaseSession,
) -> None:
    try:
        delete_canned_response(response_id, current_user, session)
    except OperationResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
