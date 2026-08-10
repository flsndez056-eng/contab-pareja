import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

BudgetMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class CategoryBudgetInput(BaseModel):
    category_id: uuid.UUID
    limit: BudgetMoney


class MonthlyBudgetUpdate(BaseModel):
    total_limit: BudgetMoney | None = None
    categories: list[CategoryBudgetInput] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def unique_categories(self) -> "MonthlyBudgetUpdate":
        category_ids = [item.category_id for item in self.categories]
        if len(category_ids) != len(set(category_ids)):
            raise ValueError("Cada categoría solo puede aparecer una vez.")
        return self


class BudgetAmountStatus(BaseModel):
    limit: Decimal | None
    spent: Decimal
    remaining: Decimal | None
    used_percent: Decimal | None
    exceeded: bool


class CategoryBudgetStatus(BudgetAmountStatus):
    category_id: uuid.UUID | None
    category_name: str


class MonthlyBudgetResponse(BaseModel):
    month: str
    currency: str
    total: BudgetAmountStatus
    categories: list[CategoryBudgetStatus]
