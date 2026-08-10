import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import transaction
from app.models.entities import ClientErrorReport, CoupleMember
from app.schemas.diagnostics import ClientErrorCreate

logger = logging.getLogger(__name__)


async def record_client_error(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: ClientErrorCreate,
) -> None:
    now = datetime.now(UTC)
    if data.occurred_at < now - timedelta(days=7) or data.occurred_at > now + timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha del diagnóstico está fuera del rango permitido.",
        )
    recent_count = await session.scalar(
        select(func.count(ClientErrorReport.id)).where(
            ClientErrorReport.user_id == user_id,
            ClientErrorReport.created_at >= now - timedelta(hours=1),
        )
    )
    if (recent_count or 0) >= 20:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Se alcanzó el límite privado de diagnósticos.",
        )
    couple_id = await session.scalar(
        select(CoupleMember.couple_id).where(
            CoupleMember.user_id == user_id,
            CoupleMember.left_at.is_(None),
        )
    )
    async with transaction(session):
        session.add(
            ClientErrorReport(
                user_id=user_id,
                couple_id=couple_id,
                app_version=data.app_version,
                error_type=data.error_type,
                fingerprint=data.fingerprint,
                stack_frames=data.stack_frames,
                screen=data.screen,
                occurred_at=data.occurred_at,
            )
        )
        await session.execute(
            delete(ClientErrorReport).where(
                ClientErrorReport.created_at < now - timedelta(days=30)
            )
        )
    logger.warning(
        "client_error fingerprint=%s type=%s version=%s",
        data.fingerprint[:12],
        data.error_type,
        data.app_version,
    )
