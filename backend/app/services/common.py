import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import CoupleMember


async def require_membership(session: AsyncSession, user_id: uuid.UUID) -> CoupleMember:
    member = await session.scalar(select(CoupleMember).where(CoupleMember.user_id == user_id))
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primero debes pertenecer a una pareja.",
        )
    return member


async def require_complete_couple(session: AsyncSession, member: CoupleMember) -> CoupleMember:
    partner = await session.scalar(
        select(CoupleMember).where(
            CoupleMember.couple_id == member.couple_id,
            CoupleMember.user_id != member.user_id,
        )
    )
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La otra persona todavía no se ha unido a la pareja.",
        )
    return partner
