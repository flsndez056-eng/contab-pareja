import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_invitation_code,
    hash_invitation_token,
    new_invitation_code,
    new_invitation_token,
    verify_password,
)
from app.db.session import transaction
from app.models.entities import (
    AuditEvent,
    Couple,
    CoupleMember,
    Expense,
    ExpenseRequest,
    Invitation,
    OutboxEvent,
    RequestStatus,
    User,
)
from app.schemas.couples import (
    CoupleHistoryItem,
    CoupleStateResponse,
    CreateCoupleRequest,
    InvitationPreviewResponse,
    InvitationResponse,
    JoinCoupleRequest,
    MemberResponse,
)


async def _require_verified_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Primero debes verificar tu correo.")
    return user


async def _members(session: AsyncSession, couple_id: uuid.UUID) -> list[MemberResponse]:
    rows = (
        await session.execute(
            select(CoupleMember, User)
            .join(User, User.id == CoupleMember.user_id)
            .where(CoupleMember.couple_id == couple_id)
            .order_by(CoupleMember.slot)
        )
    ).all()
    return [
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


async def create_couple(
    session: AsyncSession, user_id: uuid.UUID, data: CreateCoupleRequest
) -> Couple:
    try:
        async with transaction(session):
            await _require_verified_user(session, user_id)
            membership = await session.scalar(
                select(CoupleMember.id).where(
                    CoupleMember.user_id == user_id,
                    CoupleMember.left_at.is_(None),
                )
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
        await _require_verified_user(session, user_id)
        member = await session.scalar(
            select(CoupleMember).where(
                CoupleMember.user_id == user_id,
                CoupleMember.left_at.is_(None),
            )
        )
        if member is None:
            raise HTTPException(status_code=409, detail="Primero debes crear una pareja.")
        occupied = await session.scalar(
            select(CoupleMember.id).where(
                CoupleMember.couple_id == member.couple_id,
                CoupleMember.slot == 2,
                CoupleMember.left_at.is_(None),
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
        token, token_hash = new_invitation_token()
        expires_at = now + timedelta(hours=24)
        session.add(
            Invitation(
                couple_id=member.couple_id,
                created_by=user_id,
                code_hash=code_hash,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
    base_url = str(settings.invitation_base_url).rstrip("/")
    invite_url = f"{base_url}?token={quote(token, safe='')}"
    return InvitationResponse(code=code, expires_at=expires_at, invite_url=invite_url)


async def preview_invitation(session: AsyncSession, token: str) -> InvitationPreviewResponse:
    now = datetime.now(UTC)
    row = (
        await session.execute(
            select(Invitation, Couple, User)
            .join(Couple, Couple.id == Invitation.couple_id)
            .join(User, User.id == Invitation.created_by)
            .where(Invitation.token_hash == hash_invitation_token(token))
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Invitación inválida o expirada.")
    invitation, couple, inviter = row
    if (
        invitation.used_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= now
        or couple.ended_at is not None
    ):
        raise HTTPException(status_code=404, detail="Invitación inválida o expirada.")
    return InvitationPreviewResponse(
        couple_name=couple.name,
        inviter_name=inviter.display_name,
        expires_at=invitation.expires_at,
    )


async def join_couple(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: JoinCoupleRequest,
) -> Couple:
    try:
        async with transaction(session):
            await _require_verified_user(session, user_id)
            own_membership = await session.scalar(
                select(CoupleMember.id).where(
                    CoupleMember.user_id == user_id,
                    CoupleMember.left_at.is_(None),
                )
            )
            if own_membership:
                raise HTTPException(status_code=409, detail="Ya perteneces a una pareja.")

            now = datetime.now(UTC)
            lookup = (
                Invitation.code_hash == hash_invitation_code(data.code)
                if data.code is not None
                else Invitation.token_hash == hash_invitation_token(data.token or "")
            )
            invitation = await session.scalar(
                select(Invitation).where(lookup).with_for_update()
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
            if couple is None or couple.ended_at is not None:
                raise HTTPException(status_code=404, detail="Pareja no encontrada.")
            slot_two = await session.scalar(
                select(CoupleMember.id).where(
                    CoupleMember.couple_id == couple.id,
                    CoupleMember.slot == 2,
                    CoupleMember.left_at.is_(None),
                )
            )
            if slot_two:
                raise HTTPException(status_code=409, detail="La pareja ya tiene dos miembros.")

            session.add(CoupleMember(couple_id=couple.id, user_id=user_id, slot=2, role="member"))
            invitation.used_by = user_id
            invitation.used_at = now
            session.add(
                OutboxEvent(
                    aggregate_type="couple",
                    aggregate_id=couple.id,
                    event_type="couple.joined",
                    payload={
                        "recipient_user_id": str(invitation.created_by),
                        "couple_id": str(couple.id),
                    },
                )
            )
        return couple
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="La pareja ya tiene dos miembros.") from exc


async def get_state(session: AsyncSession, user_id: uuid.UUID) -> CoupleStateResponse:
    member = await session.scalar(
        select(CoupleMember).where(
            CoupleMember.user_id == user_id,
            CoupleMember.left_at.is_(None),
        )
    )
    if member is None:
        return CoupleStateResponse(couple=None, members=[])
    couple = await session.get(Couple, member.couple_id)
    if couple is None or couple.ended_at is not None:
        return CoupleStateResponse(couple=None, members=[])
    return CoupleStateResponse(couple=couple, members=await _members(session, couple.id))


async def get_history(session: AsyncSession, user_id: uuid.UUID) -> list[CoupleHistoryItem]:
    rows = (
        await session.execute(
            select(CoupleMember, Couple)
            .join(Couple, Couple.id == CoupleMember.couple_id)
            .where(
                CoupleMember.user_id == user_id,
                CoupleMember.left_at.is_not(None),
                Couple.ended_at.is_not(None),
            )
            .order_by(Couple.ended_at.desc())
        )
    ).all()
    history: list[CoupleHistoryItem] = []
    for _, couple in rows:
        expense_count, total = (
            await session.execute(
                select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0)).where(
                    Expense.couple_id == couple.id
                )
            )
        ).one()
        history.append(
            CoupleHistoryItem(
                couple=couple,
                members=await _members(session, couple.id),
                expense_count=int(expense_count),
                total=str(total),
            )
        )
    return history


async def end_active_couple(
    session: AsyncSession,
    user_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID | None:
    member = await session.scalar(
        select(CoupleMember)
        .where(CoupleMember.user_id == user_id, CoupleMember.left_at.is_(None))
        .with_for_update()
    )
    if member is None:
        return None
    couple = await session.scalar(
        select(Couple).where(Couple.id == member.couple_id).with_for_update()
    )
    if couple is None or couple.ended_at is not None:
        return None

    members = list(
        (
            await session.scalars(
                select(CoupleMember)
                .where(
                    CoupleMember.couple_id == couple.id,
                    CoupleMember.left_at.is_(None),
                )
                .with_for_update()
            )
        ).all()
    )
    pending = list(
        (
            await session.scalars(
                select(ExpenseRequest)
                .where(
                    ExpenseRequest.couple_id == couple.id,
                    ExpenseRequest.status == RequestStatus.PENDING,
                )
                .with_for_update()
            )
        ).all()
    )
    for request in pending:
        request.status = RequestStatus.CANCELLED
        request.cancelled_at = now
        request.version += 1
    active_invitations = (
        await session.scalars(
            select(Invitation).where(
                Invitation.couple_id == couple.id,
                Invitation.used_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
        )
    ).all()
    for invitation in active_invitations:
        invitation.revoked_at = now
    for current_member in members:
        current_member.left_at = now
    couple.ended_at = now
    couple.ended_by_user_id = user_id

    events: list[AuditEvent | OutboxEvent] = [
        AuditEvent(
            couple_id=couple.id,
            actor_id=user_id,
            entity_type="couple",
            entity_id=couple.id,
            event_type="couple.ended",
            data={"cancelled_pending": len(pending)},
        )
    ]
    for current_member in members:
        if current_member.user_id != user_id:
            events.append(
                OutboxEvent(
                    aggregate_type="couple",
                    aggregate_id=couple.id,
                    event_type="couple.ended",
                    payload={
                        "recipient_user_id": str(current_member.user_id),
                        "couple_id": str(couple.id),
                    },
                )
            )
    session.add_all(events)
    return couple.id


async def end_current_couple(
    session: AsyncSession,
    user_id: uuid.UUID,
    password: str,
) -> None:
    async with transaction(session):
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="La contraseña es incorrecta.")
        if await end_active_couple(session, user_id, datetime.now(UTC)) is None:
            raise HTTPException(status_code=409, detail="No tienes una pareja activa.")
