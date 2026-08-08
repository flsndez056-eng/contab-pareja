import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-user-password")
JWT_ALGORITHM = "HS256"


class TokenError(ValueError):
    pass


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    auth_version: int


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(user_id: uuid.UUID, auth_version: int = 1) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "ver": auth_version,
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM), expires_at


def decode_access_token_claims(token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise TokenError("Tipo de token inválido.")
        auth_version = int(payload.get("ver", 1))
        if auth_version < 1:
            raise TokenError("Versión de sesión inválida.")
        return AccessTokenClaims(
            user_id=uuid.UUID(str(payload["sub"])),
            auth_version=auth_version,
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise TokenError("Token inválido o expirado.") from exc


def decode_access_token(token: str) -> uuid.UUID:
    return decode_access_token_claims(token).user_id


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_email_action_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_email_action_token(raw)


def hash_email_action_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_invitation_code() -> tuple[str, str]:
    code = "-".join((secrets.token_hex(2), secrets.token_hex(2))).upper()
    return code, hashlib.sha256(code.encode("ascii")).hexdigest()


def hash_invitation_code(code: str) -> str:
    normalized = code.strip().upper()
    return hashlib.sha256(normalized.encode("ascii")).hexdigest()


def new_invitation_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_invitation_token(raw)


def hash_invitation_token(raw: str) -> str:
    return hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()
