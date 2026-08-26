from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession, PasswordReadyUser
from app.schemas.notification import NotificationPage, NotificationRead
from app.services.notifications import (
    NotificationNotFoundError,
    list_notifications,
    mark_notification_read,
)

router = APIRouter()
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("", response_model=NotificationPage)
def list_own_notifications(
    current_user: PasswordReadyUser,
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> NotificationPage:
    return list_notifications(current_user, session, page, page_size)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    current_user: PasswordReadyUser,
    session: DatabaseSession,
) -> NotificationRead:
    try:
        notification = mark_notification_read(notification_id, current_user, session)
    except NotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return NotificationRead.model_validate(notification)
