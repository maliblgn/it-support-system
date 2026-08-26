from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import DatabaseSession, PasswordReadyUser, SettingsDependency
from app.schemas.attachment import AttachmentRead
from app.services.attachments import (
    AttachmentConflictError,
    AttachmentNotFoundError,
    AttachmentValidationError,
    attachment_file_path,
    delete_own_attachment,
    get_authorized_attachment,
    store_attachment,
)
from app.services.tickets import TicketConflictError, TicketNotFoundError, get_user_ticket

router = APIRouter()
UploadedFile = Annotated[UploadFile, File(description="PNG, JPG/JPEG veya PDF dosyası")]


def _not_found(exc: LookupError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: RuntimeError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    ticket_id: int,
    file: UploadedFile,
    current_user: PasswordReadyUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> AttachmentRead:
    try:
        ticket = get_user_ticket(ticket_id, current_user, session)
        attachment = await store_attachment(ticket, current_user, file, session, settings)
    except (TicketNotFoundError, AttachmentNotFoundError) as exc:
        raise _not_found(exc) from exc
    except (TicketConflictError, AttachmentConflictError) as exc:
        raise _conflict(exc) from exc
    except AttachmentValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    return AttachmentRead.model_validate(attachment)


@router.get("/{ticket_id}/attachments/{attachment_id}", response_class=FileResponse)
def download_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: PasswordReadyUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> FileResponse:
    try:
        attachment = get_authorized_attachment(
            ticket_id,
            attachment_id,
            current_user,
            session,
        )
        path = attachment_file_path(attachment, settings)
    except (AttachmentNotFoundError, AttachmentValidationError) as exc:
        raise _not_found(exc) from exc
    return FileResponse(
        path=path,
        media_type=attachment.content_type,
        filename=attachment.original_file_name,
    )


@router.delete(
    "/{ticket_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: PasswordReadyUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> None:
    try:
        delete_own_attachment(
            ticket_id,
            attachment_id,
            current_user,
            session,
            settings,
        )
    except AttachmentNotFoundError as exc:
        raise _not_found(exc) from exc
    except AttachmentConflictError as exc:
        raise _conflict(exc) from exc
