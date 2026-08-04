import asyncio
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import (
    Couple,
    CoupleMember,
    Expense,
    ExpenseDecision,
    ExpenseRequest,
    User,
)
from app.schemas.expenses import DecisionRequest
from app.services.expenses import decide_expense_request

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Requiere PostgreSQL de integración."
)


@pytest.mark.asyncio
async def test_only_one_concurrent_decision_wins() -> None:
    raw_url = os.environ["TEST_DATABASE_URL"]
    url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    async with factory() as session, session.begin():
        session.add_all(
            [
                User(
                    id=first_id,
                    email="first@example.com",
                    password_hash="unused",
                    display_name="First",
                ),
                User(
                    id=second_id,
                    email="second@example.com",
                    password_hash="unused",
                    display_name="Second",
                ),
            ]
        )
        couple = Couple(name="Test")
        session.add(couple)
        await session.flush()
        session.add_all(
            [
                CoupleMember(couple_id=couple.id, user_id=first_id, slot=1, role="owner"),
                CoupleMember(couple_id=couple.id, user_id=second_id, slot=2, role="member"),
            ]
        )
        request = ExpenseRequest(
            couple_id=couple.id,
            requested_by=first_id,
            payment_source="joint",
            paid_by_user_id=None,
            amount=Decimal("100.00"),
            currency="DOP",
            description="Concurrent test",
            occurred_at=datetime.now(UTC),
            status="pending",
        )
        session.add(request)
        await session.flush()
        request_id = request.id

    async def decide(decision: str) -> object:
        async with factory() as session:
            return await decide_expense_request(
                session,
                second_id,
                request_id,
                DecisionRequest(
                    decision=decision,
                    reason="No corresponde" if decision == "reject" else None,
                ),
            )

    results = await asyncio.gather(decide("approve"), decide("reject"), return_exceptions=True)
    assert sum(not isinstance(result, Exception) for result in results) == 1
    loser = next(result for result in results if isinstance(result, Exception))
    assert isinstance(loser, HTTPException)
    assert loser.status_code == 409

    async with factory() as session:
        request = await session.get(ExpenseRequest, request_id)
        decisions = await session.scalar(
            select(func.count())
            .select_from(ExpenseDecision)
            .where(ExpenseDecision.request_id == request_id)
        )
        expenses = await session.scalar(
            select(func.count()).select_from(Expense).where(Expense.request_id == request_id)
        )
    assert request is not None
    assert decisions == 1
    assert expenses == (1 if request.status == "approved" else 0)
    await engine.dispose()
