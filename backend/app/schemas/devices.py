import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterDeviceRequest(BaseModel):
    installation_id: str = Field(min_length=8, max_length=255)
    fcm_registration_id: str = Field(min_length=16, max_length=4096)
    platform: str = Field(default="android", pattern="^android$")


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    installation_id: str
    platform: str
    enabled: bool
    last_seen_at: datetime
