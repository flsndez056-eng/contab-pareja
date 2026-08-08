import asyncio

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import email

client = TestClient(app)


def test_reset_password_page_exposes_app_link_and_manual_code() -> None:
    token = "safe-reset-token-123456"  # noqa: S105

    response = client.get("/auth/reset-password", params={"token": token})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert f"contabpareja://auth/reset-password?token={token}" in response.text
    assert token in response.text
    assert response.headers["referrer-policy"] == "no-referrer"


def test_action_page_escapes_untrusted_token() -> None:
    token = "1234567890123456<script>alert(1)</script>"  # noqa: S105

    response = client.get("/auth/verify-email", params={"token": token})

    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_invitation_page_opens_android_and_keeps_manual_fallback() -> None:
    token = "safe-invitation-token-12345678901234567890"  # noqa: S105

    response = client.get("/invite", params={"token": token})

    assert response.status_code == 200
    assert f"contabpareja://invite?token={token}" in response.text
    assert token in response.text
    assert response.headers["referrer-policy"] == "no-referrer"


def test_asset_links_publishes_configured_certificate(monkeypatch) -> None:
    fingerprint = "AA:BB:CC"
    monkeypatch.setattr(settings, "android_app_cert_sha256", fingerprint)

    response = client.get("/.well-known/assetlinks.json")

    assert response.status_code == 200
    assert response.json()[0]["target"] == {
        "namespace": "android_app",
        "package_name": "com.flsndez.contabpareja",
        "sha256_cert_fingerprints": [fingerprint],
    }


def test_password_reset_email_uses_https_action_page(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def capture(to_address: str, subject: str, body: str) -> None:
        captured.update(to=to_address, subject=subject, body=body)

    monkeypatch.setattr(email, "_deliver", capture)
    monkeypatch.setattr(settings, "email_delivery_mode", "smtp")

    assert asyncio.run(
        email.send_password_reset_email("person@example.com", "Persona", "token-123")
    )
    assert "https://contab.siptrapollo.online/auth/reset-password?token=token-123" in captured[
        "body"
    ]
