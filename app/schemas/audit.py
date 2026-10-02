from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class AuditLogResponse(ORMModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID
    previous_state: dict | None
    new_state: dict | None
    details: dict | None
    timestamp: datetime
