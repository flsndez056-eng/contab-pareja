import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.models.entities import RefreshSession, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenPair


async def _issue_tokens(session: AsyncSession, user_id: uuid.UUID) -> TokenPair:
    access_token, access_expires_at = create_access_token(user_id)
    raw_refresh, refresh_hash = new_refresh_token()
    session.add(
        RefreshSession(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await session.flush()
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        access_expires_at=access_expires_at,
    )


async def register(session: AsyncSession, data: RegisterRequest) -> AuthResponse:
    try:
        async with session.begin():
            existing = await session.scalar(select(User.id).where(User.email == str(data.email)))
            if existing:
                raise HTTPException(status_code=409, detail="El correo ya está registrado.")
            user = User(
                email=str(data.email),
                password_hash=hash_password(data.password),
                display_name=data.display_name,
            )
            session.add(user)
            await session.flush()
            tokens = await _issue_tokens(session, user.id)
        return AuthResponse(user=user, tokens=tokens)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="El correo ya está registrado.") from exc


async def login(session: AsyncSession, data: LoginRequest) -> AuthResponse:
    async with session.begin():
        user = await session.scalar(select(User).where(User.email == str(data.email)))
        encoded = user.password_hash if user else DUMMY_PASSWORD_HASH
        password_ok = verify_password(data.password, encoded)
        if user is None or not password_ok or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tokens = await _issue_tokens(session, user.id)
    return AuthResponse(user=user, tokens=tokens)


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> TokenPair:
    token_hash = hash_refresh_token(raw_token)
    async with session.begin():
        current = await session.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
        )
        now = datetime.now(UTC)
        if current is None or current.revoked_at is not None or current.expires_at <= now:
            raise HTTPException(status_code=401, detail="Refresh token inválido o expirado.")

        tokens = await _issue_tokens(session, current.user_id)
        replacement = await session.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == hash_refresh_token(tokens.refresh_token)
            )
        )
        current.revoked_at = now
        current.rotated_to_id = replacement.id if replacement else None
    return tokens


async def logout(session: AsyncSession, raw_token: str) -> None:
    async with session.begin():
        refresh = await session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )
        if refresh and refresh.revoked_at is None:
            refresh.revoked_at = datetime.now(UTC)
