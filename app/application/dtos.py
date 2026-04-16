from domain.entities.request import NotificationStatus, NotificationType
from pydantic import BaseModel, Field


class CreateRequestDTO(BaseModel):
    to: str = Field(..., examples=["user@example.com"])
    message: str = Field(..., examples=["Your verification code is 1234"])
    type: NotificationType = Field(..., examples=["email"])


class CreateResponseDTO(BaseModel):
    id: str = Field(..., examples=["123e4567-e89b-12d3-a456-426614174000"])


class StatusResponseDTO(BaseModel):
    id: str = Field(..., examples=["123e4567-e89b-12d3-a456-426614174000"])
    status: NotificationStatus = Field(..., examples=["queued"])


class StartProcessResultDTO(BaseModel):
    found: bool
    should_process: bool
    status: NotificationStatus | None = None
