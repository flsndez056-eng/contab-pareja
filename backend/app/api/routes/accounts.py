from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.auth import DeleteAccountRequest
from app.services import accounts as service

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    data: DeleteAccountRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Response:
    await service.delete_account(session, current_user.id, data.password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
