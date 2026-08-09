import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.models.entities import Category
from app.schemas.expenses import (
    CreateExpenseRequest,
    DecisionRequest,
    ExpenseRequestResponse,
    ReportSummaryResponse,
)
from app.services import expenses as service

router = APIRouter(tags=["expenses"])


@router.get("/categories")
async def categories(session: SessionDep, current_user: CurrentUser) -> list[dict[str, object]]:
    del current_user
    rows = (
        await session.scalars(select(Category).order_by(Category.sort_order, Category.name))
    ).all()
    return [{"id": row.id, "slug": row.slug, "name": row.name, "icon": row.icon} for row in rows]


@router.post(
    "/expense-requests",
    response_model=ExpenseRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    data: CreateExpenseRequest,
    session: SessionDep,
    current_user: CurrentUser,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> ExpenseRequestResponse:
    request = await service.create_expense_request(session, current_user.id, data, idempotency_key)
    return ExpenseRequestResponse.model_validate(request)


@router.get("/expense-requests", response_model=list[ExpenseRequestResponse])
async def requests(
    session: SessionDep,
    current_user: CurrentUser,
    box: Literal["all", "inbox", "outbox"] = "all",
    request_status: Annotated[
        Literal["pending", "approved", "rejected", "cancelled", "expired"] | None,
        Query(alias="status"),
    ] = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    category_id: uuid.UUID | None = None,
    search: Annotated[str | None, Query(alias="q", min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExpenseRequestResponse]:
    rows = await service.list_requests(
        session,
        current_user.id,
        box,
        request_status,
        from_date,
        to_date,
        category_id,
        search,
        limit,
        offset,
    )
    return [ExpenseRequestResponse.model_validate(row) for row in rows]


@router.post(
    "/expense-requests/{request_id}/decision",
    response_model=ExpenseRequestResponse,
)
async def decide_request(
    request_id: uuid.UUID,
    data: DecisionRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpenseRequestResponse:
    request = await service.decide_expense_request(session, current_user.id, request_id, data)
    return ExpenseRequestResponse.model_validate(request)


@router.post(
    "/expense-requests/{request_id}/cancel",
    response_model=ExpenseRequestResponse,
)
async def cancel_request(
    request_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExpenseRequestResponse:
    request = await service.cancel_expense_request(session, current_user.id, request_id)
    return ExpenseRequestResponse.model_validate(request)


@router.get("/reports/summary", response_model=ReportSummaryResponse)
async def summary(
    from_date: datetime,
    to_date: datetime,
    session: SessionDep,
    current_user: CurrentUser,
) -> ReportSummaryResponse:
    return await service.report_summary(session, current_user.id, from_date, to_date)
