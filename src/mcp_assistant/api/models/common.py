from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int


class HealthResponse(BaseModel):
    status: str
