import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditEvent, User

logger = logging.getLogger(__name__)


def record_audit_event(
    session: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor.id if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=(
            json.dumps(details, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            if details
            else None
        ),
    )
    session.add(event)
    logger.info(
        "Denetim olayı kaydedildi.",
        extra={
            "user_id": actor.id if actor is not None else None,
        },
    )
    return event
