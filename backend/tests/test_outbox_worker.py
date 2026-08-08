import uuid
from types import SimpleNamespace

from firebase_admin import messaging

from app.workers.outbox import classify_delivery_failures, notification_copy


def test_notification_copy_covers_expense_request() -> None:
    assert notification_copy("expense.requested") == (
        "Nuevo gasto por revisar",
        "Tu pareja envió una solicitud.",
    )


def test_delivery_failures_disable_only_stale_fids_and_retry_other_errors() -> None:
    stale_device = SimpleNamespace(id=uuid.uuid4())
    retryable_device = SimpleNamespace(id=uuid.uuid4())
    devices = [stale_device, retryable_device]
    responses = [
        SimpleNamespace(
            success=False,
            exception=messaging.UnregisteredError("FID no registrado"),
        ),
        SimpleNamespace(
            success=False,
            exception=messaging.QuotaExceededError("Cuota temporal"),
        ),
    ]

    disabled, error_names, retryable = classify_delivery_failures(devices, responses)

    assert disabled == [stale_device.id]
    assert error_names == ["QuotaExceededError", "UnregisteredError"]
    assert retryable == 1
