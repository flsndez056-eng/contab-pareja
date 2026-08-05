import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.auth import ForgotPasswordRequest, RegisterRequest, ResetPasswordRequest
from app.schemas.devices import RegisterDeviceRequest
from app.schemas.expenses import CreateExpenseRequest, DecisionRequest


def test_registration_normalizes_identity() -> None:
    request = RegisterRequest(
        email="  PERSON@Example.COM ",
        password="a-secure-password",
        display_name="  Ana   María ",
    )
    assert str(request.email) == "person@example.com"
    assert request.display_name == "Ana María"


def test_password_recovery_normalizes_email() -> None:
    request = ForgotPasswordRequest(email="  PERSON@Example.COM ")
    assert str(request.email) == "person@example.com"


def test_password_reset_requires_a_strong_password() -> None:
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="x" * 48, new_password="short")


def test_personal_payment_requires_payer() -> None:
    with pytest.raises(ValidationError):
        CreateExpenseRequest(
            amount=Decimal("10.00"),
            description="Cena",
            payment_source="personal",
            occurred_at=datetime.now(UTC),
        )


def test_joint_payment_rejects_personal_payer() -> None:
    with pytest.raises(ValidationError):
        CreateExpenseRequest(
            amount=Decimal("10.00"),
            description="Cena",
            payment_source="joint",
            paid_by_user_id=uuid.uuid4(),
            occurred_at=datetime.now(UTC),
        )


def test_rejection_requires_reason() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest(decision="reject", reason="   ")


def test_money_rejects_more_than_two_decimals() -> None:
    with pytest.raises(ValidationError):
        CreateExpenseRequest(
            amount=Decimal("10.001"),
            description="Cena",
            payment_source="joint",
            occurred_at=datetime.now(UTC),
        )


def test_device_registration_uses_firebase_installation_id() -> None:
    request = RegisterDeviceRequest(
        installation_id="android-installation-123",
        fcm_registration_id="firebase-installation-123",
    )
    assert request.fcm_registration_id == "firebase-installation-123"
    assert "fcm_token" not in request.model_dump()
