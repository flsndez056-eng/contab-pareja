import os
import uuid

import httpx
import pytest
from sqlalchemy import delete, select

from app.api.routes import auth as auth_routes
from app.db.session import SessionFactory
from app.main import app
from app.models.entities import User

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Requiere PostgreSQL de integración."
)

@pytest.mark.asyncio
async def test_identity_recovery_and_session_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = f"identity-{uuid.uuid4()}@example.com"
    initial_password = "initial-password-123"  # noqa: S105
    reset_password = "reset-password-456"  # noqa: S105
    changed_password = "changed-password-789"  # noqa: S105
    captured: dict[str, str] = {}

    async def capture_verification(_: str, __: str, token: str) -> bool:
        captured["verification"] = token
        return True

    async def capture_reset(_: str, __: str, token: str) -> bool:
        captured["reset"] = token
        return True

    monkeypatch.setattr(
        auth_routes,
        "send_verification_email",
        capture_verification,
    )
    monkeypatch.setattr(auth_routes, "send_password_reset_email", capture_reset)

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": initial_password,
                    "display_name": "Identity Test",
                },
            )
            assert registration.status_code == 201
            initial_access = registration.json()["tokens"]["access_token"]
            assert captured["verification"]

            verification = await client.post(
                "/api/v1/auth/email/verification/confirm",
                json={"token": captured["verification"]},
            )
            assert verification.status_code == 200
            assert verification.json()["email_verified"] is True

            unknown_recovery = await client.post(
                "/api/v1/auth/password/forgot",
                json={"email": f"unknown-{uuid.uuid4()}@example.com"},
            )
            known_recovery = await client.post(
                "/api/v1/auth/password/forgot",
                json={"email": email},
            )
            assert unknown_recovery.status_code == known_recovery.status_code == 202
            assert unknown_recovery.json() == known_recovery.json()
            assert captured["reset"]

            reset = await client.post(
                "/api/v1/auth/password/reset",
                json={"token": captured["reset"], "new_password": reset_password},
            )
            assert reset.status_code == 204
            reused_reset = await client.post(
                "/api/v1/auth/password/reset",
                json={"token": captured["reset"], "new_password": changed_password},
            )
            assert reused_reset.status_code == 400

            old_session = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {initial_access}"},
            )
            assert old_session.status_code == 401
            old_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": initial_password},
            )
            assert old_login.status_code == 401

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": reset_password},
            )
            assert login.status_code == 200
            access_before_revoke = login.json()["tokens"]["access_token"]
            revoked = await client.post(
                "/api/v1/auth/sessions/revoke-all",
                headers={"Authorization": f"Bearer {access_before_revoke}"},
                json={"password": reset_password},
            )
            assert revoked.status_code == 200
            access_after_revoke = revoked.json()["tokens"]["access_token"]
            assert (
                await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {access_before_revoke}"},
                )
            ).status_code == 401

            changed = await client.post(
                "/api/v1/auth/password/change",
                headers={"Authorization": f"Bearer {access_after_revoke}"},
                json={
                    "current_password": reset_password,
                    "new_password": changed_password,
                },
            )
            assert changed.status_code == 200
            final_access = changed.json()["tokens"]["access_token"]
            assert (
                await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {access_after_revoke}"},
                )
            ).status_code == 401
            assert (
                await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {final_access}"},
                )
            ).status_code == 200
    finally:
        async with SessionFactory() as session, session.begin():
            user_id = await session.scalar(select(User.id).where(User.email == email))
            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))
