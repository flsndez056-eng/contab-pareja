from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.diagnostics import ClientErrorCreate, DiagnosticAccepted
from app.services import diagnostics as service

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.post(
    "/client-errors",
    response_model=DiagnosticAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def client_error(
    data: ClientErrorCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> DiagnosticAccepted:
    await service.record_client_error(session, current_user.id, data)
    return DiagnosticAccepted()
