import os
import uuid

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import SessionFactory
from app.main import app
from app.models.entities import Couple, CoupleMember, Invitation, User

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Requiere PostgreSQL de integración."
)


@pytest.mark.asyncio
async def test_authenticated_write_reuses_the_authentication_transaction() -> None:
    email = f"route-{uuid.uuid4()}@example.com"
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "integration-password-123",
                    "display_name": "Integration Test",
                },
            )
            assert registration.status_code == 201
            access_token = registration.json()["tokens"]["access_token"]

            response = await client.post(
                "/api/v1/couples",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "name": "Pareja de integración",
                    "default_currency": "DOP",
                    "timezone": "America/Santo_Domingo",
                },
            )

            assert response.status_code == 201
            assert response.json()["name"] == "Pareja de integración"
    finally:
        async with SessionFactory() as session, session.begin():
            user_id = await session.scalar(select(User.id).where(User.email == email))
            if user_id is not None:
                couple_id = await session.scalar(
                    select(CoupleMember.couple_id).where(CoupleMember.user_id == user_id)
                )
                if couple_id is not None:
                    await session.execute(
                        delete(Invitation).where(Invitation.couple_id == couple_id)
                    )
                    await session.execute(
                        delete(CoupleMember).where(CoupleMember.couple_id == couple_id)
                    )
                    await session.execute(delete(Couple).where(Couple.id == couple_id))
                await session.execute(delete(User).where(User.id == user_id))
