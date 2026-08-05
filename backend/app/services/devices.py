import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import transaction
from app.models.entities import Device
from app.schemas.devices import RegisterDeviceRequest


async def register_device(
    session: AsyncSession, user_id: uuid.UUID, data: RegisterDeviceRequest
) -> Device:
    async with transaction(session):
        device = await session.scalar(
            select(Device).where(Device.installation_id == data.installation_id).with_for_update()
        )
        if device is None:
            device = Device(
                user_id=user_id,
                installation_id=data.installation_id,
                fcm_registration_id=data.fcm_registration_id,
                platform=data.platform,
            )
            session.add(device)
        else:
            device.user_id = user_id
            device.fcm_registration_id = data.fcm_registration_id
            device.enabled = True
            device.last_seen_at = datetime.now(UTC)
        await session.flush()
    return device


async def disable_device(session: AsyncSession, user_id: uuid.UUID, installation_id: str) -> None:
    async with transaction(session):
        device = await session.scalar(
            select(Device).where(
                Device.installation_id == installation_id,
                Device.user_id == user_id,
            )
        )
        if device:
            device.enabled = False
