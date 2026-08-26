from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import InvalidSessionTokenError, decode_session_token
from app.db.session import get_db_session
from app.models.entities import User
from app.models.enums import UserRole

DatabaseSession = Annotated[Session, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum geçersiz veya süresi dolmuş.",
        headers={"WWW-Authenticate": "Session"},
    )


def get_current_user(
    request: Request,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise authentication_error()

    try:
        claims = decode_session_token(token, settings)
    except InvalidSessionTokenError as exc:
        raise authentication_error() from exc

    user = session.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise authentication_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _require_password_ready(current_user: User) -> None:
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Devam etmeden önce geçici şifrenizi değiştirmeniz gerekir.",
        )


def require_password_ready_user(current_user: CurrentUser) -> User:
    _require_password_ready(current_user)
    return current_user


PasswordReadyUser = Annotated[User, Depends(require_password_ready_user)]


def require_end_user(current_user: CurrentUser) -> User:
    _require_password_ready(current_user)
    if current_user.role != UserRole.USER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem yalnızca çalışan rolüne açıktır.",
        )
    return current_user


EndUser = Annotated[User, Depends(require_end_user)]


def require_it_user(current_user: CurrentUser) -> User:
    _require_password_ready(current_user)
    if current_user.role != UserRole.IT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem yalnızca bilgi işlem rolüne açıktır.",
        )
    return current_user


ItUser = Annotated[User, Depends(require_it_user)]


def require_admin_user(current_user: CurrentUser) -> User:
    _require_password_ready(current_user)
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem yalnızca yönetici rolüne açıktır.",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin_user)]


def require_it_or_admin_user(current_user: CurrentUser) -> User:
    _require_password_ready(current_user)
    if current_user.role not in {UserRole.IT.value, UserRole.ADMIN.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem yalnızca bilgi işlem veya yönetici rolüne açıktır.",
        )
    return current_user


ItOrAdminUser = Annotated[User, Depends(require_it_or_admin_user)]


def authorize_resource_owner(current_user: User, owner_user_id: int) -> None:
    if current_user.id == owner_user_id or current_user.role in {
        UserRole.IT.value,
        UserRole.ADMIN.value,
    }:
        return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Kaynak bulunamadı.",
    )
