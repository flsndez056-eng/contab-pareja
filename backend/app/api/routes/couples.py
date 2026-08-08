from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.couples import (
    CoupleHistoryItem,
    CoupleResponse,
    CoupleStateResponse,
    CreateCoupleRequest,
    EndCoupleRequest,
    InvitationPreviewResponse,
    InvitationResponse,
    JoinCoupleRequest,
)
from app.services import couples as service

router = APIRouter(prefix="/couples", tags=["couples"])


@router.get("/current", response_model=CoupleStateResponse)
async def current_couple(session: SessionDep, current_user: CurrentUser) -> CoupleStateResponse:
    return await service.get_state(session, current_user.id)


@router.get("/history", response_model=list[CoupleHistoryItem])
async def couple_history(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[CoupleHistoryItem]:
    return await service.get_history(session, current_user.id)


@router.post("", response_model=CoupleResponse, status_code=status.HTTP_201_CREATED)
async def create_couple(
    data: CreateCoupleRequest, session: SessionDep, current_user: CurrentUser
) -> CoupleResponse:
    couple = await service.create_couple(session, current_user.id, data)
    return CoupleResponse.model_validate(couple)


@router.post("/invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(session: SessionDep, current_user: CurrentUser) -> InvitationResponse:
    return await service.create_invitation(session, current_user.id)


@router.get("/invitations/preview", response_model=InvitationPreviewResponse)
async def invitation_preview(
    session: SessionDep,
    token: str = Query(min_length=32, max_length=512),
) -> InvitationPreviewResponse:
    return await service.preview_invitation(session, token)


@router.post("/join", response_model=CoupleResponse)
async def join_couple(
    data: JoinCoupleRequest, session: SessionDep, current_user: CurrentUser
) -> CoupleResponse:
    couple = await service.join_couple(session, current_user.id, data)
    return CoupleResponse.model_validate(couple)


@router.post("/current/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_current_couple(
    data: EndCoupleRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    await service.end_current_couple(session, current_user.id, data.password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
