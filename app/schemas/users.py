from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DemoUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    title: str | None
    facility_id: UUID | None
    facility_name: str | None
    role_code: str
    role_name: str
    is_active: bool
    last_login_at: datetime | None
    is_demo_user: bool
