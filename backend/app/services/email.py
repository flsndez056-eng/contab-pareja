import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)


def _deliver(to_address: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.email_from_address:
        raise RuntimeError("La entrega SMTP no está configurada.")

    message = EmailMessage()
    message["From"] = str(settings.email_from_address)
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    ) as client:
        client.ehlo()
        if settings.smtp_starttls:
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if settings.smtp_username:
            if settings.smtp_password is None:
                raise RuntimeError(
                    "SMTP_PASSWORD es obligatorio cuando SMTP_USERNAME está definido."
                )
            client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        client.send_message(message)


async def send_account_email(to_address: str, subject: str, body: str) -> bool:
    if settings.email_delivery_mode == "disabled":
        logger.warning("Entrega de correo deshabilitada; no se envió una acción de cuenta.")
        return False
    try:
        await asyncio.to_thread(_deliver, to_address, subject, body)
        return True
    except Exception:
        logger.exception("No se pudo entregar un correo de acción de cuenta.")
        return False


async def send_verification_email(to_address: str, display_name: str, token: str) -> bool:
    base_url = str(settings.account_action_base_url).rstrip("/")
    link = f"{base_url}/verify-email?token={quote(token, safe='')}"
    body = (
        f"Hola, {display_name}.\n\n"
        "Confirma tu correo de DúoCuenta abriendo este enlace:\n"
        f"{link}\n\n"
        f"También puedes copiar este código en la aplicación:\n{token}\n\n"
        f"El código vence en {settings.email_verification_hours} horas. "
        "Si no creaste esta cuenta, ignora el mensaje."
    )
    return await send_account_email(to_address, "Confirma tu correo de DúoCuenta", body)


async def send_password_reset_email(to_address: str, display_name: str, token: str) -> bool:
    base_url = str(settings.account_action_base_url).rstrip("/")
    link = f"{base_url}/reset-password?token={quote(token, safe='')}"
    body = (
        f"Hola, {display_name}.\n\n"
        "Recibimos una solicitud para cambiar tu contraseña de DúoCuenta.\n"
        f"Abre este enlace:\n{link}\n\n"
        f"También puedes copiar este código en la aplicación:\n{token}\n\n"
        f"El código vence en {settings.password_reset_minutes} minutos. "
        "Si no solicitaste el cambio, ignora el mensaje."
    )
    return await send_account_email(to_address, "Recupera tu acceso a DúoCuenta", body)
