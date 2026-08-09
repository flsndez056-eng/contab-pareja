import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import transaction
from app.models.entities import (
    AuditEvent,
    Category,
    Couple,
    Expense,
    ExpenseDecision,
    ExpenseRequest,
    IdempotencyRecord,
    OutboxEvent,
    RequestStatus,
)
from app.schemas.expenses import (
    CategoryTotal,
    CreateExpenseRequest,
    DecisionRequest,
    ReportSummaryResponse,
)
from app.services.common import require_complete_couple, require_membership


def _request_event_payload(request: ExpenseRequest, recipient_id: uuid.UUID) -> dict[str, str]:
    return {
        "request_id": str(request.id),
        "recipient_user_id": str(recipient_id),
        "amount": str(request.amount),
        "currency": request.currency,
        "status": request.status,
    }


async def create_expense_request(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: CreateExpenseRequest,
    idempotency_key: str,
) -> ExpenseRequest:
    body_hash = hashlib.sha256(data.model_dump_json().encode("utf-8")).hexdigest()
    async with transaction(session):
        previous = await session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.scope == "create-expense-request",
                IdempotencyRecord.key == idempotency_key,
            )
        )
        if previous:
            if previous.request_hash != body_hash:
                raise HTTPException(
                    status_code=409,
                    detail="La clave de idempotencia ya fue usada con otros datos.",
                )
            request_id = uuid.UUID(previous.response_body["request_id"])
            existing = await session.get(ExpenseRequest, request_id)
            if existing is None:
                raise HTTPException(status_code=409, detail="Registro idempotente inconsistente.")
            return existing

        member = await require_membership(session, user_id)
        partner = await require_complete_couple(session, member)
        couple = await session.get(Couple, member.couple_id)
        if couple is None:
            raise HTTPException(status_code=409, detail="La pareja ya no existe.")
        if data.currency != couple.default_currency:
            raise HTTPException(
                status_code=422,
                detail=f"La moneda activa de la pareja es {couple.default_currency}.",
            )

        if data.payment_source == "personal":
            allowed_payers = {member.user_id, partner.user_id}
            if data.paid_by_user_id not in allowed_payers:
                raise HTTPException(status_code=422, detail="El pagador no pertenece a la pareja.")
        if data.category_id and await session.get(Category, data.category_id) is None:
            raise HTTPException(status_code=422, detail="Categoría inválida.")

        request = ExpenseRequest(
            couple_id=member.couple_id,
            requested_by=user_id,
            paid_by_user_id=data.paid_by_user_id,
            payment_source=data.payment_source,
            category_id=data.category_id,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            merchant=data.merchant,
            occurred_at=data.occurred_at,
            status=RequestStatus.PENDING,
        )
        session.add(request)
        await session.flush()
        session.add_all(
            [
                AuditEvent(
                    couple_id=member.couple_id,
                    actor_id=user_id,
                    entity_type="expense_request",
                    entity_id=request.id,
                    event_type="expense.requested",
                    data={"amount": str(request.amount), "currency": request.currency},
                ),
                OutboxEvent(
                    aggregate_type="expense_request",
                    aggregate_id=request.id,
                    event_type="expense.requested",
                    payload=_request_event_payload(request, partner.user_id),
                ),
                IdempotencyRecord(
                    user_id=user_id,
                    scope="create-expense-request",
                    key=idempotency_key,
                    request_hash=body_hash,
                    response_status=201,
                    response_body={"request_id": str(request.id)},
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                ),
            ]
        )
        await session.flush()
        await session.refresh(request)
    return request


async def decide_expense_request(
    session: AsyncSession,
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    data: DecisionRequest,
) -> ExpenseRequest:
    async with transaction(session):
        request = await session.scalar(
            select(ExpenseRequest).where(ExpenseRequest.id == request_id).with_for_update()
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
        member = await require_membership(session, user_id)
        if member.couple_id != request.couple_id:
            raise HTTPException(status_code=403, detail="No puedes decidir esta solicitud.")
        if request.requested_by == user_id:
            raise HTTPException(status_code=403, detail="No puedes decidir tu propia solicitud.")
        if request.status != RequestStatus.PENDING:
            raise HTTPException(status_code=409, detail="La solicitud ya fue resuelta.")

        now = datetime.now(UTC)
        approved = data.decision == "approve"
        request.status = RequestStatus.APPROVED if approved else RequestStatus.REJECTED
        request.rejection_reason = None if approved else data.reason
        request.resolved_by = user_id
        request.resolved_at = now
        request.version += 1
        session.add(
            ExpenseDecision(
                request_id=request.id,
                decided_by=user_id,
                decision=data.decision,
                reason=data.reason,
            )
        )

        if approved:
            session.add(
                Expense(
                    request_id=request.id,
                    couple_id=request.couple_id,
                    requested_by=request.requested_by,
                    paid_by_user_id=request.paid_by_user_id,
                    payment_source=request.payment_source,
                    category_id=request.category_id,
                    amount=request.amount,
                    currency=request.currency,
                    description=request.description,
                    merchant=request.merchant,
                    occurred_at=request.occurred_at,
                    approved_by=user_id,
                    approved_at=now,
                )
            )

        event_type = "expense.approved" if approved else "expense.rejected"
        payload = _request_event_payload(request, request.requested_by)
        session.add_all(
            [
                AuditEvent(
                    couple_id=request.couple_id,
                    actor_id=user_id,
                    entity_type="expense_request",
                    entity_id=request.id,
                    event_type=event_type,
                    data={"reason": data.reason} if data.reason else {},
                ),
                OutboxEvent(
                    aggregate_type="expense_request",
                    aggregate_id=request.id,
                    event_type=event_type,
                    payload=payload,
                ),
            ]
        )
        await session.flush()
        await session.refresh(request)
    return request


async def cancel_expense_request(
    session: AsyncSession, user_id: uuid.UUID, request_id: uuid.UUID
) -> ExpenseRequest:
    async with transaction(session):
        request = await session.scalar(
            select(ExpenseRequest).where(ExpenseRequest.id == request_id).with_for_update()
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
        if request.requested_by != user_id:
            raise HTTPException(status_code=403, detail="Solo el solicitante puede cancelarla.")
        if request.status != RequestStatus.PENDING:
            raise HTTPException(status_code=409, detail="La solicitud ya fue resuelta.")
        member = await require_membership(session, user_id)
        partner = await require_complete_couple(session, member)
        now = datetime.now(UTC)
        request.status = RequestStatus.CANCELLED
        request.cancelled_at = now
        request.version += 1
        session.add_all(
            [
                AuditEvent(
                    couple_id=request.couple_id,
                    actor_id=user_id,
                    entity_type="expense_request",
                    entity_id=request.id,
                    event_type="expense.cancelled",
                    data={},
                ),
                OutboxEvent(
                    aggregate_type="expense_request",
                    aggregate_id=request.id,
                    event_type="expense.cancelled",
                    payload=_request_event_payload(request, partner.user_id),
                ),
            ]
        )
        await session.flush()
        await session.refresh(request)
    return request


async def list_requests(
    session: AsyncSession,
    user_id: uuid.UUID,
    box: str,
    request_status: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    category_id: uuid.UUID | None,
    search: str | None,
    limit: int,
    offset: int,
) -> list[ExpenseRequest]:
    if from_date and to_date:
        if to_date <= from_date:
            raise HTTPException(status_code=422, detail="to_date debe ser posterior a from_date.")
        if to_date - from_date > timedelta(days=366):
            raise HTTPException(status_code=422, detail="El rango máximo es de 366 días.")
    member = await require_membership(session, user_id)
    query = select(ExpenseRequest).where(ExpenseRequest.couple_id == member.couple_id)
    if box == "inbox":
        query = query.where(ExpenseRequest.requested_by != user_id)
    elif box == "outbox":
        query = query.where(ExpenseRequest.requested_by == user_id)
    if request_status:
        query = query.where(ExpenseRequest.status == request_status)
    if from_date:
        query = query.where(ExpenseRequest.created_at >= from_date)
    if to_date:
        query = query.where(ExpenseRequest.created_at < to_date)
    if category_id:
        query = query.where(ExpenseRequest.category_id == category_id)
    if search and (term := search.strip()):
        query = query.where(
            or_(
                ExpenseRequest.description.icontains(term, autoescape=True),
                ExpenseRequest.merchant.icontains(term, autoescape=True),
            )
        )
    result = await session.scalars(
        query.order_by(ExpenseRequest.created_at.desc(), ExpenseRequest.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.all())


async def report_summary(
    session: AsyncSession,
    user_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
) -> ReportSummaryResponse:
    if to_date <= from_date:
        raise HTTPException(status_code=422, detail="to_date debe ser posterior a from_date.")
    if to_date - from_date > timedelta(days=366):
        raise HTTPException(status_code=422, detail="El rango máximo es de 366 días.")
    member = await require_membership(session, user_id)

    totals = (
        await session.execute(
            select(
                func.coalesce(func.sum(Expense.amount), 0),
                func.coalesce(
                    func.sum(Expense.amount).filter(Expense.payment_source == "personal"), 0
                ),
                func.coalesce(
                    func.sum(Expense.amount).filter(Expense.payment_source == "joint"), 0
                ),
                func.count(Expense.id),
            ).where(
                Expense.couple_id == member.couple_id,
                Expense.occurred_at >= from_date,
                Expense.occurred_at < to_date,
            )
        )
    ).one()
    category_rows = (
        await session.execute(
            select(
                Expense.category_id,
                func.coalesce(Category.name, "Sin categoría"),
                func.sum(Expense.amount),
            )
            .outerjoin(Category, Category.id == Expense.category_id)
            .where(
                Expense.couple_id == member.couple_id,
                Expense.occurred_at >= from_date,
                Expense.occurred_at < to_date,
            )
            .group_by(Expense.category_id, Category.name)
            .order_by(func.sum(Expense.amount).desc())
        )
    ).all()
    currency = await session.scalar(
        select(Couple.default_currency).where(Couple.id == member.couple_id)
    )
    if currency is None:
        raise HTTPException(status_code=409, detail="La pareja ya no existe.")
    return ReportSummaryResponse(
        currency=currency,
        from_date=from_date,
        to_date=to_date,
        total=Decimal(totals[0]),
        personal_total=Decimal(totals[1]),
        joint_total=Decimal(totals[2]),
        expense_count=totals[3],
        categories=[
            CategoryTotal(category_id=row[0], category_name=row[1], total=Decimal(row[2]))
            for row in category_rows
        ],
    )
