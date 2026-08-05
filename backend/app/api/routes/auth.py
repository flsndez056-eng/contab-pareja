from fastapi import APIRouter, BackgroundTasks, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ConfirmEmailRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ReauthenticateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserResponse,
)
from app.services import auth as service
from app.services.email import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> AuthResponse:
    response = await service.register(session, data)
    delivery = await service.request_email_verification(session, response.user.id)
    if delivery is not None:
        background_tasks.add_task(send_verification_email, *delivery)
    return response


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, session: SessionDep) -> AuthResponse:
    return await service.login(session, data)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, session: SessionDep) -> TokenPair:
    return await service.rotate_refresh_token(session, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: LogoutRequest, session: SessionDep) -> Response:
    await service.logout(session, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/password/forgot",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    data: ForgotPasswordRequest,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    delivery = await service.request_password_reset(session, str(data.email))
    if delivery is not None:
        background_tasks.add_task(send_password_reset_email, *delivery)
    return MessageResponse(
        message="Si el correo está registrado, recibirás instrucciones para recuperar el acceso."
    )


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: ResetPasswordRequest, session: SessionDep) -> Response:
    await service.reset_password(session, data.token, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/change", response_model=AuthResponse)
async def change_password(
    data: ChangePasswordRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> AuthResponse:
    return await service.change_password(session, current_user.id, data)


@router.post(
    "/email/verification/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_email_verification(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    delivery = await service.request_email_verification(session, current_user.id)
    if delivery is not None:
        background_tasks.add_task(send_verification_email, *delivery)
    return MessageResponse(message="Si corresponde, recibirás un correo de verificación.")


@router.post("/email/verification/confirm", response_model=UserResponse)
async def confirm_email(data: ConfirmEmailRequest, session: SessionDep) -> UserResponse:
    user = await service.confirm_email(session, data.token)
    return UserResponse.model_validate(user)


@router.post("/sessions/revoke-all", response_model=AuthResponse)
async def revoke_all_sessions(
    data: ReauthenticateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> AuthResponse:
    return await service.revoke_all_sessions(session, current_user.id, data.password)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
