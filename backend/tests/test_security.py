import uuid

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_invitation_code,
    hash_password,
    new_invitation_code,
    new_refresh_token,
    verify_password,
)


def test_password_round_trip() -> None:
    encoded = hash_password("a-strong-example-password")
    assert encoded != "a-strong-example-password"
    assert verify_password("a-strong-example-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_round_trip() -> None:
    user_id = uuid.uuid4()
    token, expires_at = create_access_token(user_id)
    assert decode_access_token(token) == user_id
    assert expires_at.tzinfo is not None


def test_invalid_access_token_is_rejected() -> None:
    with pytest.raises(TokenError):
        decode_access_token("not-a-jwt")


def test_refresh_tokens_are_only_persisted_as_hashes() -> None:
    raw, digest = new_refresh_token()
    assert raw != digest
    assert len(digest) == 64


def test_invitation_hash_is_normalized() -> None:
    code, digest = new_invitation_code()
    assert len(code) == 9
    assert hash_invitation_code(code.lower()) == digest
