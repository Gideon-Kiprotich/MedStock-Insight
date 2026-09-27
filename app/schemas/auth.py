import uuid

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoleResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str


class UserResponse(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    role: RoleResponse
