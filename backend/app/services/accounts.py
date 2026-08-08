import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.session import transaction
from app.models.entities import (
    AuditEvent,
    Device,
    EmailActionToken,
    RefreshSession,
    User,
)
from app.services.couples import end_active_couple


async def delete_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    password: str,
) -> None:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña es incorrecta.")

        now = datetime.now(UTC)
        await end_active_couple(session, user.id, now)
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await session.execute(
            update(EmailActionToken)
            .where(EmailActionToken.user_id == user.id, EmailActionToken.used_at.is_(None))
            .values(used_at=now)
        )
        await session.execute(
            update(Device).where(Device.user_id == user.id).values(enabled=False)
        )
        session.add(
            AuditEvent(
                couple_id=None,
                actor_id=user.id,
                entity_type="user",
                entity_id=user.id,
                event_type="account.deleted",
                data={},
            )
        )
        user.email = f"deleted-{user.id.hex}@deleted.invalid"
        user.display_name = "Cuenta eliminada"
        user.password_hash = hash_password(secrets.token_urlsafe(48))
        user.email_verified = False
        user.is_active = False
        user.auth_version += 1
        user.deleted_at = now
