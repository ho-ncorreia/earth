from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models import AuditEvent, User


def record_event(
    db: Session,
    *,
    actor: User | None,
    action: str,
    object_type: str,
    object_id: str = "",
    previous_value: dict | None = None,
    new_value: dict | None = None,
    correlation_id: str = "",
    origin: str = "web",
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system",
        action=action,
        object_type=object_type,
        object_id=object_id,
        previous_value=jsonable_encoder(previous_value) if previous_value is not None else None,
        new_value=jsonable_encoder(new_value) if new_value is not None else None,
        correlation_id=correlation_id,
        origin=origin,
    )
    db.add(event)
    return event