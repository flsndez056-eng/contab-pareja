import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

import firebase_admin
from firebase_admin import messaging
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionFactory, dispose_engine
from app.models.entities import Device, OutboxEvent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def initialize_firebase() -> bool:
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        if not settings.fcm_project_id:
            return False
        firebase_admin.initialize_app(options={"projectId": settings.fcm_project_id})
        return True


def notification_copy(event_type: str) -> tuple[str, str]:
    messages = {
        "expense.requested": ("Nuevo gasto por revisar", "Tu pareja envió una solicitud."),
        "expense.approved": ("Gasto aprobado", "Tu solicitud fue aprobada."),
        "expense.rejected": ("Gasto rechazado", "Tu solicitud fue rechazada."),
        "expense.cancelled": ("Solicitud cancelada", "La solicitud pendiente fue cancelada."),
    }
    return messages.get(event_type, ("Contab Pareja", "Hay una actualización pendiente."))


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
    if response.failure_count:
        logger.warning("FCM tuvo %s fallo(s) para %s", response.failure_count, event.id)


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
    try:
        while True:
            processed = await process_one()
            if not processed:
                await asyncio.sleep(1)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(run())
