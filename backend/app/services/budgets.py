import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import transaction
from app.models.entities import AuditEvent, Category, Couple, Expense, MonthlyBudget
from app.schemas.budgets import (
    BudgetAmountStatus,
    CategoryBudgetStatus,
    MonthlyBudgetResponse,
    MonthlyBudgetUpdate,
)
from app.services.common import require_membership


def parse_month(value: str) -> date:
    try:
        parsed = datetime.strptime(value, "%Y-%m").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El mes debe usar el formato YYYY-MM.",
        ) from exc
    return parsed.replace(day=1)


def month_bounds(month: date, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    next_month = (
        date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
    )
    start = datetime(month.year, month.month, 1, tzinfo=zone).astimezone(UTC)
    end = datetime(next_month.year, next_month.month, 1, tzinfo=zone).astimezone(UTC)
    return start, end


def amount_status(limit: Decimal | None, spent: Decimal) -> BudgetAmountStatus:
    remaining = limit - spent if limit is not None else None
    used_percent = None
    if limit is not None:
        used_percent = (spent * Decimal(100) / limit).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
    return BudgetAmountStatus(
        limit=limit,
        spent=spent,
        remaining=remaining,
        used_percent=used_percent,
        exceeded=limit is not None and spent > limit,
    )


async def get_monthly_budget(
    session: AsyncSession,
    user_id: uuid.UUID,
    month_value: str,
) -> MonthlyBudgetResponse:
    month = parse_month(month_value)
    member = await require_membership(session, user_id)
    couple = await session.get(Couple, member.couple_id)
    if couple is None:
        raise HTTPException(status_code=409, detail="La pareja ya no existe.")
    start, end = month_bounds(month, couple.timezone)

    budget_rows = list(
        (
            await session.scalars(
                select(MonthlyBudget).where(
                    MonthlyBudget.couple_id == member.couple_id,
                    MonthlyBudget.month == month,
                )
            )
        ).all()
    )
    total_limit = next(
        (row.limit_amount for row in budget_rows if row.category_id is None), None
    )
    category_limits = {
        row.category_id: row.limit_amount for row in budget_rows if row.category_id is not None
    }

    total_spent = Decimal(
        await session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.couple_id == member.couple_id,
                Expense.occurred_at >= start,
                Expense.occurred_at < end,
            )
        )
        or 0
    )
    spent_rows = (
        await session.execute(
            select(
                Expense.category_id,
                func.coalesce(Category.name, "Sin categoría"),
                func.sum(Expense.amount),
            )
            .outerjoin(Category, Category.id == Expense.category_id)
            .where(
                Expense.couple_id == member.couple_id,
                Expense.occurred_at >= start,
                Expense.occurred_at < end,
            )
            .group_by(Expense.category_id, Category.name)
        )
    ).all()
    spent_by_category = {row[0]: (row[1], Decimal(row[2])) for row in spent_rows}
    configured_names: dict[uuid.UUID, str] = {}
    if category_limits:
        name_rows = (
            await session.execute(
                select(Category.id, Category.name).where(Category.id.in_(category_limits))
            )
        ).all()
        configured_names = {category_id: name for category_id, name in name_rows}
    category_ids = set(category_limits) | set(spent_by_category)
    categories: list[CategoryBudgetStatus] = []
    for category_id in category_ids:
        category_name, spent = spent_by_category.get(
            category_id,
            (configured_names.get(category_id, "Sin categoría"), Decimal(0)),
        )
        status_value = amount_status(category_limits.get(category_id), spent)
        categories.append(
            CategoryBudgetStatus(
                category_id=category_id,
                category_name=category_name,
                **status_value.model_dump(),
            )
        )
    categories.sort(key=lambda item: item.spent, reverse=True)
    return MonthlyBudgetResponse(
        month=month.strftime("%Y-%m"),
        currency=couple.default_currency,
        total=amount_status(total_limit, total_spent),
        categories=categories,
    )


async def replace_monthly_budget(
    session: AsyncSession,
    user_id: uuid.UUID,
    month_value: str,
    data: MonthlyBudgetUpdate,
) -> MonthlyBudgetResponse:
    month = parse_month(month_value)
    member = await require_membership(session, user_id)
    couple = await session.get(Couple, member.couple_id)
    if couple is None:
        raise HTTPException(status_code=409, detail="La pareja ya no existe.")
    category_ids = {item.category_id for item in data.categories}
    if category_ids:
        existing_ids = set(
            (await session.scalars(select(Category.id).where(Category.id.in_(category_ids)))).all()
        )
        if existing_ids != category_ids:
            raise HTTPException(status_code=422, detail="Una o más categorías no existen.")

    async with transaction(session):
        await session.execute(
            delete(MonthlyBudget).where(
                MonthlyBudget.couple_id == member.couple_id,
                MonthlyBudget.month == month,
            )
        )
        if data.total_limit is not None:
            session.add(
                MonthlyBudget(
                    couple_id=member.couple_id,
                    month=month,
                    category_id=None,
                    limit_amount=data.total_limit,
                    currency=couple.default_currency,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )
        session.add_all(
            [
                MonthlyBudget(
                    couple_id=member.couple_id,
                    month=month,
                    category_id=item.category_id,
                    limit_amount=item.limit,
                    currency=couple.default_currency,
                    created_by=user_id,
                    updated_by=user_id,
                )
                for item in data.categories
            ]
        )
        session.add(
            AuditEvent(
                couple_id=member.couple_id,
                actor_id=user_id,
                entity_type="monthly_budget",
                entity_id=member.couple_id,
                event_type="monthly_budget.updated",
                data={
                    "month": month.strftime("%Y-%m"),
                    "has_total_limit": data.total_limit is not None,
                    "category_limit_count": len(data.categories),
                },
            )
        )
    return await get_monthly_budget(session, user_id, month_value)
