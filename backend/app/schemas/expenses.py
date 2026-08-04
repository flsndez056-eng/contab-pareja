import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class CreateExpenseRequest(BaseModel):
    amount: Money
    currency: str = Field(default="DOP", min_length=3, max_length=3)
    description: str = Field(min_length=2, max_length=1000)
    merchant: str | None = Field(default=None, max_length=160)
    category_id: uuid.UUID | None = None
    payment_source: Literal["personal", "joint"]
    paid_by_user_id: uuid.UUID | None = None
    occurred_at: datetime

    @model_validator(mode="after")
    def validate_payer(self) -> "CreateExpenseRequest":
        self.currency = self.currency.upper()
        self.description = self.description.strip()
        self.merchant = self.merchant.strip() if self.merchant else None
        if self.payment_source == "personal" and self.paid_by_user_id is None:
            raise ValueError("paid_by_user_id es obligatorio para un pago personal.")
        if self.payment_source == "joint" and self.paid_by_user_id is not None:
            raise ValueError("Una cuenta conjunta no debe indicar paid_by_user_id.")
        return self


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "DecisionRequest":
        self.reason = self.reason.strip() if self.reason else None
        if self.decision == "reject" and not self.reason:
            raise ValueError("El motivo de rechazo es obligatorio.")
        if self.decision == "approve":
            self.reason = None
        return self


class ExpenseRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    couple_id: uuid.UUID
    requested_by: uuid.UUID
    paid_by_user_id: uuid.UUID | None
    payment_source: str
    category_id: uuid.UUID | None
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    occurred_at: datetime
    status: str
    rejection_reason: str | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    couple_id: uuid.UUID
    requested_by: uuid.UUID
    paid_by_user_id: uuid.UUID | None
    payment_source: str
    category_id: uuid.UUID | None
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    occurred_at: datetime
    approved_by: uuid.UUID
    approved_at: datetime
    created_at: datetime


class CategoryTotal(BaseModel):
    category_id: uuid.UUID | None
    category_name: str
    total: Decimal


class ReportSummaryResponse(BaseModel):
    currency: str
    from_date: datetime
    to_date: datetime
    total: Decimal
    personal_total: Decimal
    joint_total: Decimal
    expense_count: int
    categories: list[CategoryTotal]
