import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    ended_at: datetime | None


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
    invite_url: str


class InvitationPreviewResponse(BaseModel):
    couple_name: str
    inviter_name: str
    expires_at: datetime


class JoinCoupleRequest(BaseModel):
    code: str | None = Field(default=None, min_length=9, max_length=9)
    token: str | None = Field(default=None, min_length=32, max_length=512)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @model_validator(mode="after")
    def exactly_one_credential(self) -> Self:
        if (self.code is None) == (self.token is None):
            raise ValueError("Envía un código o un token de invitación.")
        return self


class EndCoupleRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class CoupleHistoryItem(BaseModel):
    couple: CoupleResponse
    members: list[MemberResponse]
    expense_count: int
    total: str
