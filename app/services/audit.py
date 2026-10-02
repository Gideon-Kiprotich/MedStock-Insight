from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core import AuditLog


def log_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: UUID,
    user_id: UUID | None = None,
    previous_state: dict[str, Any] | None = None,
    new_state: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Creates an immutable audit log entry within the current database session."""
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_state=previous_state,
        new_state=new_state,
        details=details,
    )
    db.add(log_entry)
    db.flush()
    return log_entry
