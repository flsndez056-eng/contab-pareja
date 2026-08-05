import os
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import SessionFactory
from app.main import app
from app.models.entities import (
    AuditEvent,
    Couple,
    CoupleMember,
    Expense,
    ExpenseDecision,
    ExpenseRequest,
    Invitation,
    OutboxEvent,
    User,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Requiere PostgreSQL de integración."
)


@pytest.mark.asyncio
async def test_authenticated_write_reuses_the_authentication_transaction() -> None:
    test_id = uuid.uuid4()
    owner_email = f"route-owner-{test_id}@example.com"
    partner_email = f"route-partner-{test_id}@example.com"
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            owner_registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": owner_email,
                    "password": "integration-password-123",
                    "display_name": "Integration Owner",
                },
            )
            partner_registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": partner_email,
                    "password": "integration-password-456",
                    "display_name": "Integration Partner",
                },
            )
            assert owner_registration.status_code == 201
            assert partner_registration.status_code == 201
            owner_data = owner_registration.json()
            partner_data = partner_registration.json()
            owner_headers = {
                "Authorization": f"Bearer {owner_data['tokens']['access_token']}"
            }
            partner_headers = {
                "Authorization": f"Bearer {partner_data['tokens']['access_token']}"
            }

            couple_response = await client.post(
                "/api/v1/couples",
                headers=owner_headers,
                json={
                    "name": "Pareja de integración",
                    "default_currency": "DOP",
                    "timezone": "America/Santo_Domingo",
                },
            )
            assert couple_response.status_code == 201
            assert couple_response.json()["name"] == "Pareja de integración"

            invitation = await client.post(
                "/api/v1/couples/invitations", headers=owner_headers
            )
            assert invitation.status_code == 201
            joined = await client.post(
                "/api/v1/couples/join",
                headers=partner_headers,
                json={"code": invitation.json()["code"]},
            )
            assert joined.status_code == 200

            request = await client.post(
                "/api/v1/expense-requests",
                headers={**owner_headers, "Idempotency-Key": f"route-{test_id}"},
                json={
                    "amount": "125.50",
                    "currency": "DOP",
                    "description": "Gasto de integración",
                    "merchant": "Comercio de prueba",
                    "payment_source": "personal",
                    "paid_by_user_id": owner_data["user"]["id"],
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
            )
            assert request.status_code == 201
            assert request.json()["status"] == "pending"

            decision = await client.post(
                f"/api/v1/expense-requests/{request.json()['id']}/decision",
                headers=partner_headers,
                json={"decision": "approve"},
            )
            assert decision.status_code == 200
            assert decision.json()["status"] == "approved"
            assert decision.json()["updated_at"]
    finally:
        async with SessionFactory() as session, session.begin():
            user_ids = list(
                (
                    await session.scalars(
                        select(User.id).where(User.email.in_([owner_email, partner_email]))
                    )
                ).all()
            )
            if user_ids:
                couple_id = await session.scalar(
                    select(CoupleMember.couple_id).where(CoupleMember.user_id.in_(user_ids)).limit(1)
                )
                if couple_id is not None:
                    request_ids = select(ExpenseRequest.id).where(
                        ExpenseRequest.couple_id == couple_id
                    )
                    await session.execute(
                        delete(OutboxEvent).where(OutboxEvent.aggregate_id.in_(request_ids))
                    )
                    await session.execute(
                        delete(AuditEvent).where(AuditEvent.couple_id == couple_id)
                    )
                    await session.execute(delete(Expense).where(Expense.couple_id == couple_id))
                    await session.execute(
                        delete(ExpenseDecision).where(
                            ExpenseDecision.request_id.in_(request_ids)
                        )
                    )
                    await session.execute(
                        delete(ExpenseRequest).where(ExpenseRequest.couple_id == couple_id)
                    )
                    await session.execute(
                        delete(Invitation).where(Invitation.couple_id == couple_id)
                    )
                    await session.execute(
                        delete(CoupleMember).where(CoupleMember.couple_id == couple_id)
                    )
                    await session.execute(delete(Couple).where(Couple.id == couple_id))
                await session.execute(delete(User).where(User.id.in_(user_ids)))
