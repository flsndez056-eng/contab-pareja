import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_invitation_code, new_invitation_code
from app.db.session import transaction
from app.models.entities import Couple, CoupleMember, Invitation, User
from app.schemas.couples import (
    CoupleStateResponse,
    CreateCoupleRequest,
    InvitationResponse,
    MemberResponse,
)


async def create_couple(
    session: AsyncSession, user_id: uuid.UUID, data: CreateCoupleRequest
) -> Couple:
    try:
        async with transaction(session):
            membership = await session.scalar(
                select(CoupleMember.id).where(CoupleMember.user_id == user_id)
            )
            if membership:
                raise HTTPException(status_code=409, detail="Ya perteneces a una pareja.")
            couple = Couple(
                name=data.name.strip(),
                default_currency=data.default_currency,
                timezone=data.timezone,
            )
            session.add(couple)
            await session.flush()
            session.add(CoupleMember(couple_id=couple.id, user_id=user_id, slot=1, role="owner"))
        return couple
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="No se pudo crear la pareja.") from exc


async def create_invitation(session: AsyncSession, user_id: uuid.UUID) -> InvitationResponse:
    async with transaction(session):
        member = await session.scalar(select(CoupleMember).where(CoupleMember.user_id == user_id))
        if member is None:
            raise HTTPException(status_code=409, detail="Primero debes crear una pareja.")
        occupied = await session.scalar(
            select(CoupleMember.id).where(
                CoupleMember.couple_id == member.couple_id,
                CoupleMember.slot == 2,
            )
        )
        if occupied:
            raise HTTPException(status_code=409, detail="La pareja ya tiene dos miembros.")

        now = datetime.now(UTC)
        active_invitations = (
            await session.scalars(
                select(Invitation).where(
                    Invitation.couple_id == member.couple_id,
                    Invitation.used_at.is_(None),
                    Invitation.revoked_at.is_(None),
                    Invitation.expires_at > now,
                )
            )
        ).all()
        for invite in active_invitations:
            invite.revoked_at = now

        code, code_hash = new_invitation_code()
        expires_at = now + timedelta(hours=24)
        session.add(
            Invitation(
                couple_id=member.couple_id,
                created_by=user_id,
                code_hash=code_hash,
                expires_at=expires_at,
            )
        )
    return InvitationResponse(code=code, expires_at=expires_at)


async def join_couple(session: AsyncSession, user_id: uuid.UUID, code: str) -> Couple:
    try:
        async with transaction(session):
            own_membership = await session.scalar(
                select(CoupleMember.id).where(CoupleMember.user_id == user_id)
            )
            if own_membership:
                raise HTTPException(status_code=409, detail="Ya perteneces a una pareja.")

            now = datetime.now(UTC)
            invitation = await session.scalar(
                select(Invitation)
                .where(Invitation.code_hash == hash_invitation_code(code))
                .with_for_update()
            )
            if (
                invitation is None
                or invitation.used_at is not None
                or invitation.revoked_at is not None
                or invitation.expires_at <= now
            ):
                raise HTTPException(status_code=404, detail="Invitación inválida o expirada.")

            couple = await session.scalar(
                select(Couple).where(Couple.id == invitation.couple_id).with_for_update()
            )
            if couple is None:
                raise HTTPException(status_code=404, detail="Pareja no encontrada.")
            slot_two = await session.scalar(
                select(CoupleMember.id).where(
                    CoupleMember.couple_id == couple.id,
                    CoupleMember.slot == 2,
                )
            )
            if slot_two:
                raise HTTPException(status_code=409, detail="La pareja ya tiene dos miembros.")

            session.add(CoupleMember(couple_id=couple.id, user_id=user_id, slot=2, role="member"))
            invitation.used_by = user_id
            invitation.used_at = now
        return couple
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="La pareja ya tiene dos miembros.") from exc


async def get_state(session: AsyncSession, user_id: uuid.UUID) -> CoupleStateResponse:
    member = await session.scalar(select(CoupleMember).where(CoupleMember.user_id == user_id))
    if member is None:
        return CoupleStateResponse(couple=None, members=[])
    couple = await session.get(Couple, member.couple_id)
    rows = (
        await session.execute(
            select(CoupleMember, User)
            .join(User, User.id == CoupleMember.user_id)
            .where(CoupleMember.couple_id == member.couple_id)
            .order_by(CoupleMember.slot)
        )
    ).all()
    members = [
        MemberResponse(
            user_id=row_user.id,
            display_name=row_user.display_name,
            email=row_user.email,
            slot=row_member.slot,
            role=row_member.role,
            joined_at=row_member.joined_at,
        )
        for row_member, row_user in rows
    ]
    return CoupleStateResponse(couple=couple, members=members)
