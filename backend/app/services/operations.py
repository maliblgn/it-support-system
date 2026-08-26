from datetime import UTC, datetime

from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.models.entities import CannedResponse, User
from app.schemas.operations import CannedResponseCreate, CannedResponseUpdate
from app.services.audit import record_audit_event


class OperationResourceNotFoundError(LookupError):
    pass


def list_canned_responses(
    session: Session, *, include_inactive: bool = False
) -> list[CannedResponse]:
    query = select(CannedResponse)
    if not include_inactive:
        query = query.where(CannedResponse.is_active == true())
    return list(session.scalars(query.order_by(CannedResponse.title, CannedResponse.id)).all())


def create_canned_response(
    payload: CannedResponseCreate,
    actor: User,
    session: Session,
) -> CannedResponse:
    response = CannedResponse(
        title=payload.title,
        content=payload.content,
        is_active=True,
        created_by=actor.id,
    )
    session.add(response)
    session.flush()
    record_audit_event(
        session,
        actor,
        "CANNED_RESPONSE_CREATED",
        "CANNED_RESPONSE",
        response.id,
        {"title": response.title},
    )
    session.commit()
    session.refresh(response)
    return response


def update_canned_response(
    response_id: int,
    payload: CannedResponseUpdate,
    actor: User,
    session: Session,
) -> CannedResponse:
    response = session.get(CannedResponse, response_id)
    if response is None:
        raise OperationResourceNotFoundError("Hazır cevap bulunamadı.")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(response, field, value)
    response.updated_at = datetime.now(UTC).replace(tzinfo=None)
    record_audit_event(
        session,
        actor,
        "CANNED_RESPONSE_UPDATED",
        "CANNED_RESPONSE",
        response.id,
        {"changed_fields": sorted(changes)},
    )
    session.commit()
    session.refresh(response)
    return response


def delete_canned_response(response_id: int, actor: User, session: Session) -> None:
    response = session.get(CannedResponse, response_id)
    if response is None:
        raise OperationResourceNotFoundError("Hazır cevap bulunamadı.")
    response.is_active = False
    response.updated_at = datetime.now(UTC).replace(tzinfo=None)
    record_audit_event(
        session,
        actor,
        "CANNED_RESPONSE_DEACTIVATED",
        "CANNED_RESPONSE",
        response.id,
        {"title": response.title},
    )
    session.commit()
