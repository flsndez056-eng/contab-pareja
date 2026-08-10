from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.budgets import MonthlyBudgetResponse, MonthlyBudgetUpdate
from app.services import budgets as service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/{month}", response_model=MonthlyBudgetResponse)
async def get_budget(
    month: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> MonthlyBudgetResponse:
    return await service.get_monthly_budget(session, current_user.id, month)


@router.put("/{month}", response_model=MonthlyBudgetResponse)
async def replace_budget(
    month: str,
    data: MonthlyBudgetUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> MonthlyBudgetResponse:
    return await service.replace_monthly_budget(session, current_user.id, month, data)
