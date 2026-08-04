from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.couples import (
    CoupleResponse,
    CoupleStateResponse,
    CreateCoupleRequest,
    InvitationResponse,
    JoinCoupleRequest,
)
from app.services import couples as service

router = APIRouter(prefix="/couples", tags=["couples"])


@router.get("/current", response_model=CoupleStateResponse)
async def current_couple(session: SessionDep, current_user: CurrentUser) -> CoupleStateResponse:
    return await service.get_state(session, current_user.id)


@router.post("", response_model=CoupleResponse, status_code=status.HTTP_201_CREATED)
async def create_couple(
    data: CreateCoupleRequest, session: SessionDep, current_user: CurrentUser
) -> CoupleResponse:
    couple = await service.create_couple(session, current_user.id, data)
    return CoupleResponse.model_validate(couple)


@router.post("/invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(session: SessionDep, current_user: CurrentUser) -> InvitationResponse:
    return await service.create_invitation(session, current_user.id)


@router.post("/join", response_model=CoupleResponse)
async def join_couple(
    data: JoinCoupleRequest, session: SessionDep, current_user: CurrentUser
) -> CoupleResponse:
    couple = await service.join_couple(session, current_user.id, data.code)
    return CoupleResponse.model_validate(couple)
