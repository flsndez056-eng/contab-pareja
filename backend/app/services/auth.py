import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_email_action_token,
    hash_password,
    hash_refresh_token,
    new_email_action_token,
    new_refresh_token,
    verify_password,
)
from app.db.session import transaction
from app.models.entities import EmailActionPurpose, EmailActionToken, RefreshSession, User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenPair,
)

EmailDelivery = tuple[str, str, str]


async def _issue_tokens(session: AsyncSession, user: User) -> TokenPair:
    access_token, access_expires_at = create_access_token(user.id, user.auth_version)
    raw_refresh, refresh_hash = new_refresh_token()
    session.add(
        RefreshSession(
            user_id=user.id,
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


async def _revoke_all_sessions(session: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    await session.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def _issue_email_action_token(
    session: AsyncSession,
    user: User,
    purpose: EmailActionPurpose,
    lifetime: timedelta,
) -> str | None:
    now = datetime.now(UTC)
    latest = await session.scalar(
        select(EmailActionToken)
        .where(
            EmailActionToken.user_id == user.id,
            EmailActionToken.purpose == purpose,
            EmailActionToken.used_at.is_(None),
        )
        .order_by(EmailActionToken.created_at.desc())
        .limit(1)
    )
    if latest is not None and latest.created_at > now - timedelta(
        seconds=settings.email_action_cooldown_seconds
    ):
        return None

    await session.execute(
        update(EmailActionToken)
        .where(
            EmailActionToken.user_id == user.id,
            EmailActionToken.purpose == purpose,
            EmailActionToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw_token, token_hash = new_email_action_token()
    session.add(
        EmailActionToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=now + lifetime,
        )
    )
    await session.flush()
    return raw_token


async def _consume_email_action_token(
    session: AsyncSession,
    raw_token: str,
    purpose: EmailActionPurpose,
) -> tuple[EmailActionToken, User]:
    token = await session.scalar(
        select(EmailActionToken)
        .where(
            EmailActionToken.token_hash == hash_email_action_token(raw_token),
            EmailActionToken.purpose == purpose,
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    if token is None or token.used_at is not None or token.expires_at <= now:
        raise HTTPException(status_code=400, detail="El código es inválido o ya expiró.")
    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="El código es inválido o ya expiró.")
    return token, user


async def register(session: AsyncSession, data: RegisterRequest) -> AuthResponse:
    try:
        async with transaction(session):
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
            tokens = await _issue_tokens(session, user)
        return AuthResponse(user=user, tokens=tokens)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="El correo ya está registrado.") from exc


async def login(session: AsyncSession, data: LoginRequest) -> AuthResponse:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.email == str(data.email)))
        encoded = user.password_hash if user else DUMMY_PASSWORD_HASH
        password_ok = verify_password(data.password, encoded)
        if user is None or not password_ok or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tokens = await _issue_tokens(session, user)
    return AuthResponse(user=user, tokens=tokens)


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> TokenPair:
    token_hash = hash_refresh_token(raw_token)
    async with transaction(session):
        current = await session.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
        )
        now = datetime.now(UTC)
        if current is None or current.revoked_at is not None or current.expires_at <= now:
            raise HTTPException(status_code=401, detail="Refresh token inválido o expirado.")
        user = await session.get(User, current.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Refresh token inválido o expirado.")

        tokens = await _issue_tokens(session, user)
        replacement = await session.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == hash_refresh_token(tokens.refresh_token)
            )
        )
        current.revoked_at = now
        current.rotated_to_id = replacement.id if replacement else None
    return tokens


async def logout(session: AsyncSession, raw_token: str) -> None:
    async with transaction(session):
        refresh = await session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )
        if refresh and refresh.revoked_at is None:
            refresh.revoked_at = datetime.now(UTC)


async def request_email_verification(
    session: AsyncSession, user_id: uuid.UUID
) -> EmailDelivery | None:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or not user.is_active or user.email_verified:
            return None
        raw_token = await _issue_email_action_token(
            session,
            user,
            EmailActionPurpose.VERIFY_EMAIL,
            timedelta(hours=settings.email_verification_hours),
        )
        if raw_token is None:
            return None
        delivery = (user.email, user.display_name, raw_token)
    return delivery


async def confirm_email(session: AsyncSession, raw_token: str) -> User:
    async with transaction(session):
        token, user = await _consume_email_action_token(
            session, raw_token, EmailActionPurpose.VERIFY_EMAIL
        )
        now = datetime.now(UTC)
        user.email_verified = True
        token.used_at = now
        await session.execute(
            update(EmailActionToken)
            .where(
                EmailActionToken.user_id == user.id,
                EmailActionToken.purpose == EmailActionPurpose.VERIFY_EMAIL,
                EmailActionToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await session.flush()
    return user


async def request_password_reset(session: AsyncSession, email: str) -> EmailDelivery | None:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.email == email).with_for_update())
        if user is None or not user.is_active:
            hash_email_action_token(new_email_action_token()[0])
            return None
        raw_token = await _issue_email_action_token(
            session,
            user,
            EmailActionPurpose.RESET_PASSWORD,
            timedelta(minutes=settings.password_reset_minutes),
        )
        if raw_token is None:
            return None
        delivery = (user.email, user.display_name, raw_token)
    return delivery


async def reset_password(session: AsyncSession, raw_token: str, new_password: str) -> None:
    async with transaction(session):
        token, user = await _consume_email_action_token(
            session, raw_token, EmailActionPurpose.RESET_PASSWORD
        )
        now = datetime.now(UTC)
        user.password_hash = hash_password(new_password)
        user.auth_version += 1
        token.used_at = now
        await _revoke_all_sessions(session, user.id, now)
        await session.execute(
            update(EmailActionToken)
            .where(
                EmailActionToken.user_id == user.id,
                EmailActionToken.purpose == EmailActionPurpose.RESET_PASSWORD,
                EmailActionToken.used_at.is_(None),
            )
            .values(used_at=now)
        )


async def change_password(
    session: AsyncSession, user_id: uuid.UUID, data: ChangePasswordRequest
) -> AuthResponse:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
        if verify_password(data.new_password, user.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña nueva debe ser diferente.")
        now = datetime.now(UTC)
        user.password_hash = hash_password(data.new_password)
        user.auth_version += 1
        await _revoke_all_sessions(session, user.id, now)
        tokens = await _issue_tokens(session, user)
    return AuthResponse(user=user, tokens=tokens)


async def revoke_all_sessions(
    session: AsyncSession, user_id: uuid.UUID, password: str
) -> AuthResponse:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña es incorrecta.")
        now = datetime.now(UTC)
        user.auth_version += 1
        await _revoke_all_sessions(session, user.id, now)
        tokens = await _issue_tokens(session, user)
    return AuthResponse(user=user, tokens=tokens)
