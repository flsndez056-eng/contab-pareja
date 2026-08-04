import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateCoupleRequest(BaseModel):
    name: str = Field(default="Nuestra pareja", min_length=2, max_length=100)
    default_currency: str = Field(default="DOP", min_length=3, max_length=3)
    timezone: str = Field(default="America/Santo_Domingo", min_length=3, max_length=64)

    @field_validator("default_currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("La moneda debe ser un código ISO de tres letras.")
        return value.upper()


class CoupleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    default_currency: str
    timezone: str
    created_at: datetime


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    email: str
    slot: int
    role: str
    joined_at: datetime


class CoupleStateResponse(BaseModel):
    couple: CoupleResponse | None
    members: list[MemberResponse]


class InvitationResponse(BaseModel):
    code: str
    expires_at: datetime


class JoinCoupleRequest(BaseModel):
    code: str = Field(min_length=9, max_length=9)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()
