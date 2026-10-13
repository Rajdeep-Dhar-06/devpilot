from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class ApiError(BaseModel):
    code: str
    message: str
    
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ApiError | None = None