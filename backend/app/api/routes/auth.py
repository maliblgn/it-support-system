import logging

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession, SettingsDependency
from app.core.config import Settings
from app.core.security import create_csrf_token, create_session_token
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserRead
from app.services.auth import (
    DeletedAccountError,
    EmailAlreadyExistsError,
    InactiveAccountError,
    authenticate_user,
    register_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def set_auth_cookies(response: Response, user_id: int, settings: Settings) -> None:
    max_age = settings.session_lifetime_hours * 60 * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user_id, settings),
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=create_csrf_token(),
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    if not settings.public_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yeni hesap kaydı bu ortamda kapalıdır. Demo hesaplarından biriyle giriş yapın.",
        )
    try:
        user = register_user(payload, session, settings)
    except DeletedAccountError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    set_auth_cookies(response, user.id, settings)
    logger.info("Kullanıcı kaydı tamamlandı.", extra={"user_id": user.id})
    return UserRead.model_validate(user)


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    response: Response,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = authenticate_user(payload.email, payload.password, session, settings)
    except InactiveAccountError as exc:
        logger.warning("Pasif hesap giriş denemesi.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DeletedAccountError as exc:
        logger.warning("Silinmiş hesap giriş denemesi.")
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except ValueError:
        user = None
    if user is None:
        logger.warning("Başarısız giriş denemesi.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )
    set_auth_cookies(response, user.id, settings)
    logger.info("Kullanıcı giriş yaptı.", extra={"user_id": user.id, "role": user.role})
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, current_user: CurrentUser, settings: SettingsDependency) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    logger.info("Kullanıcı çıkış yaptı.", extra={"user_id": current_user.id})


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
