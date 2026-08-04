from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.devices import DeviceResponse, RegisterDeviceRequest
from app.services import devices as service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.put("/current", response_model=DeviceResponse)
async def register_device(
    data: RegisterDeviceRequest, session: SessionDep, current_user: CurrentUser
) -> DeviceResponse:
    device = await service.register_device(session, current_user.id, data)
    return DeviceResponse.model_validate(device)


@router.delete("/{installation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_device(
    installation_id: str, session: SessionDep, current_user: CurrentUser
) -> Response:
    await service.disable_device(session, current_user.id, installation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
