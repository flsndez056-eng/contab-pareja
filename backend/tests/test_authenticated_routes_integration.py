import os
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import delete, or_, select, update

from app.db.session import SessionFactory
from app.main import app
from app.models.entities import (
    AuditEvent,
    ClientErrorReport,
    Couple,
    CoupleMember,
    Expense,
    ExpenseDecision,
    ExpenseRequest,
    Invitation,
    MonthlyBudget,
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
    created_user_ids: list[uuid.UUID] = []

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
            created_user_ids.extend(
                [uuid.UUID(owner_data["user"]["id"]), uuid.UUID(partner_data["user"]["id"])]
            )
            owner_headers = {
                "Authorization": f"Bearer {owner_data['tokens']['access_token']}"
            }
            partner_headers = {
                "Authorization": f"Bearer {partner_data['tokens']['access_token']}"
            }

            async with SessionFactory() as session, session.begin():
                await session.execute(
                    update(User)
                    .where(User.email.in_([owner_email, partner_email]))
                    .values(email_verified=True)
                )

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
            token = invitation.json()["invite_url"].split("token=", maxsplit=1)[1]
            preview = await client.get(
                "/api/v1/couples/invitations/preview", params={"token": token}
            )
            assert preview.status_code == 200
            assert preview.json()["inviter_name"] == "Integration Owner"
            joined = await client.post(
                "/api/v1/couples/join",
                headers=partner_headers,
                json={"token": token},
            )
            assert joined.status_code == 200

            month = datetime.now(ZoneInfo("America/Santo_Domingo")).strftime("%Y-%m")
            budget_saved = await client.put(
                f"/api/v1/budgets/{month}",
                headers=owner_headers,
                json={"total_limit": "1000.00", "categories": []},
            )
            assert budget_saved.status_code == 200
            assert budget_saved.json()["total"]["spent"] == "0.00"

            diagnostic = await client.post(
                "/api/v1/diagnostics/client-errors",
                headers=owner_headers,
                json={
                    "app_version": "0.5.0",
                    "error_type": "java.lang.IllegalStateException",
                    "fingerprint": "a" * 64,
                    "stack_frames": [
                        "com.flsndez.contabpareja.ui.MainViewModel.refresh(MainViewModel.kt:1)"
                    ],
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
            )
            assert diagnostic.status_code == 202

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

            budget_after_expense = await client.get(
                f"/api/v1/budgets/{month}", headers=partner_headers
            )
            assert budget_after_expense.status_code == 200
            assert budget_after_expense.json()["total"]["spent"] == "125.50"
            assert budget_after_expense.json()["total"]["remaining"] == "874.50"

            now = datetime.now(UTC)
            filtered = await client.get(
                "/api/v1/expense-requests",
                headers=owner_headers,
                params={
                    "status": "approved",
                    "from_date": (now - timedelta(days=1)).isoformat(),
                    "to_date": (now + timedelta(days=1)).isoformat(),
                    "q": "integración",
                    "limit": 500,
                },
            )
            assert filtered.status_code == 200
            assert [item["id"] for item in filtered.json()] == [request.json()["id"]]

            no_match = await client.get(
                "/api/v1/expense-requests",
                headers=owner_headers,
                params={"q": "comercio inexistente"},
            )
            assert no_match.status_code == 200
            assert no_match.json() == []

            invalid_range = await client.get(
                "/api/v1/expense-requests",
                headers=owner_headers,
                params={
                    "from_date": now.isoformat(),
                    "to_date": (now - timedelta(days=1)).isoformat(),
                },
            )
            assert invalid_range.status_code == 422

            ended = await client.post(
                "/api/v1/couples/current/end",
                headers=owner_headers,
                json={"password": "integration-password-123"},
            )
            assert ended.status_code == 204
            partner_current = await client.get(
                "/api/v1/couples/current", headers=partner_headers
            )
            assert partner_current.status_code == 200
            assert partner_current.json()["couple"] is None
            history = await client.get("/api/v1/couples/history", headers=owner_headers)
            assert history.status_code == 200
            assert history.json()[0]["expense_count"] == 1
            assert history.json()[0]["total"] == "125.50"

            deleted = await client.request(
                "DELETE",
                "/api/v1/account",
                headers=partner_headers,
                json={
                    "password": "integration-password-456",
                    "confirmation": "ELIMINAR",
                },
            )
            assert deleted.status_code == 204
            registered_again = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": partner_email,
                    "password": "integration-password-789",
                    "display_name": "New Integration Account",
                },
            )
            assert registered_again.status_code == 201
            created_user_ids.append(uuid.UUID(registered_again.json()["user"]["id"]))
    finally:
        async with SessionFactory() as session, session.begin():
            user_ids = created_user_ids
            if user_ids:
                couple_id = await session.scalar(
                    select(CoupleMember.couple_id).where(CoupleMember.user_id.in_(user_ids)).limit(1)
                )
                if couple_id is not None:
                    request_ids = select(ExpenseRequest.id).where(
                        ExpenseRequest.couple_id == couple_id
                    )
                    await session.execute(
                        delete(OutboxEvent).where(
                            or_(
                                OutboxEvent.aggregate_id.in_(request_ids),
                                OutboxEvent.aggregate_id == couple_id,
                            )
                        )
                    )
                    await session.execute(
                        delete(AuditEvent).where(
                            or_(
                                AuditEvent.couple_id == couple_id,
                                AuditEvent.actor_id.in_(user_ids),
                            )
                        )
                    )
                    await session.execute(
                        delete(ClientErrorReport).where(ClientErrorReport.user_id.in_(user_ids))
                    )
                    await session.execute(
                        delete(MonthlyBudget).where(MonthlyBudget.couple_id == couple_id)
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
