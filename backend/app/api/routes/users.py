from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession, SettingsDependency
from app.schemas.user import PasswordChangeRequest, UserProfileUpdate, UserRead
from app.services.auth import (
    DeletedAccountError,
    DemoAccountProtectedError,
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
    change_user_password,
    update_user_profile,
)

router = APIRouter()


@router.get("/me", response_model=UserRead)
def get_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = update_user_profile(
            current_user,
            payload.model_dump(exclude_unset=True),
            session,
            settings,
        )
    except (DeletedAccountError, DemoAccountProtectedError, EmailAlreadyExistsError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return UserRead.model_validate(user)


@router.post("/me/password", response_model=UserRead)
def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> UserRead:
    try:
        user = change_user_password(
            current_user,
            payload.current_password,
            payload.new_password,
            session,
            settings,
        )
    except DemoAccountProtectedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return UserRead.model_validate(user)
