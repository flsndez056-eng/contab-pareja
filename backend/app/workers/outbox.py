import asyncio
import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import firebase_admin
from firebase_admin import messaging
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import SessionFactory, dispose_engine
from app.models.entities import Device, OutboxEvent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def initialize_firebase() -> bool:
    try:
        app = firebase_admin.get_app()
    except ValueError:
        if not settings.fcm_project_id:
            return False
        app = firebase_admin.initialize_app(options={"projectId": settings.fcm_project_id})
    app.credential.get_credential()
    return True


def notification_copy(event_type: str) -> tuple[str, str]:
    messages = {
        "expense.requested": ("Nuevo gasto por revisar", "Tu pareja envió una solicitud."),
        "expense.approved": ("Gasto aprobado", "Tu solicitud fue aprobada."),
        "expense.rejected": ("Gasto rechazado", "Tu solicitud fue rechazada."),
        "expense.cancelled": ("Solicitud cancelada", "La solicitud pendiente fue cancelada."),
        "couple.joined": ("Pareja conectada", "Tu pareja aceptó la invitación."),
        "couple.ended": ("Conexión finalizada", "La relación quedó archivada para ambos."),
    }
    return messages.get(event_type, ("DúoCuenta", "Hay una actualización pendiente."))


def classify_delivery_failures(
    devices: Sequence[Device], responses: Sequence[Any]
) -> tuple[list[uuid.UUID], list[str], int]:
    failures = [
        (device, result.exception)
        for device, result in zip(devices, responses, strict=True)
        if not result.success
    ]
    unregistered_ids = [
        device.id
        for device, error in failures
        if isinstance(error, messaging.UnregisteredError)
    ]
    error_names = sorted({type(error).__name__ for _, error in failures})
    retryable_failures = len(failures) - len(unregistered_ids)
    return unregistered_ids, error_names, retryable_failures


async def deliver_event(event: OutboxEvent) -> None:
    recipient_value = event.payload.get("recipient_user_id")
    if not recipient_value:
        return
    recipient = uuid.UUID(str(recipient_value))
    async with SessionFactory() as session:
        devices = (
            await session.scalars(
                select(Device).where(Device.user_id == recipient, Device.enabled.is_(True))
            )
        ).all()
    if not devices:
        return

    if not initialize_firebase():
        if settings.is_production:
            raise RuntimeError("FCM_PROJECT_ID no está configurado en producción.")
        logger.info("FCM simulado para %s dispositivo(s): %s", len(devices), event.event_type)
        return

    title, body = notification_copy(event.event_type)
    message = messaging.MulticastMessage(
        fids=[device.fcm_registration_id for device in devices],
        notification=messaging.Notification(title=title, body=body),
        data={key: str(value) for key, value in event.payload.items()},
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="expense_requests",
                visibility="private",
            ),
        ),
    )
    response = await asyncio.to_thread(messaging.send_each_for_multicast, message)
    if not response.failure_count:
        return

    unregistered_ids, error_names, retryable_failures = classify_delivery_failures(
        devices, response.responses
    )
    logger.warning(
        "FCM tuvo %s fallo(s) y %s éxito(s) para %s: %s",
        response.failure_count,
        response.success_count,
        event.id,
        ", ".join(error_names),
    )
    if unregistered_ids:
        async with SessionFactory() as session, session.begin():
            await session.execute(
                update(Device).where(Device.id.in_(unregistered_ids)).values(enabled=False)
            )
    if response.success_count == 0 and retryable_failures:
        raise RuntimeError(
            "FCM rechazó todos los destinos: " + ", ".join(error_names)
        )


async def process_one() -> bool:
    async with SessionFactory() as session, session.begin():
        now = datetime.now(UTC)
        event = await session.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.processed_at.is_(None),
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if event is None:
            return False
        event.attempts += 1
        try:
            await deliver_event(event)
            event.processed_at = now
            event.last_error = None
        except Exception as exc:
            logger.exception("No se pudo entregar el evento %s", event.id)
            event.last_error = str(exc)[:2000]
            delay = min(300, 2 ** min(event.attempts, 8))
            event.available_at = now + timedelta(seconds=delay)
    return True


async def run() -> None:
    logger.info("Worker outbox iniciado")
    if not initialize_firebase() and settings.is_production:
        raise RuntimeError("FCM_PROJECT_ID no está configurado en producción.")
    try:
        while True:
            processed = await process_one()
            if not processed:
                await asyncio.sleep(1)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(run())
