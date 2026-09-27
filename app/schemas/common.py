from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class CollectionResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: Pagination


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
