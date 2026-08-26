from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    account_email_fingerprint,
    dummy_password_hash,
    hash_password,
    validate_allowed_email,
    verify_password,
)
from app.models.entities import DeletedAccount, User
from app.models.enums import UserRole
from app.schemas.auth import RegisterRequest
from app.services.audit import record_audit_event


class EmailAlreadyExistsError(ValueError):
    pass


class InvalidCurrentPasswordError(ValueError):
    pass


class InactiveAccountError(PermissionError):
    pass


class DeletedAccountError(PermissionError):
    pass


class DemoAccountProtectedError(PermissionError):
    pass


def _is_email_unique_violation(exc: IntegrityError) -> bool:
    message = str(exc.orig).casefold()
    return "uq_users_email" in message or "unique constraint failed: users.email" in message


def register_user(payload: RegisterRequest, session: Session, settings: Settings) -> User:
    email = validate_allowed_email(payload.email, settings.allowed_email_domains)
    deleted_fingerprint = account_email_fingerprint(email, settings)
    if session.get(DeletedAccount, deleted_fingerprint) is not None:
        raise DeletedAccountError(
            "Bu e-posta adresine ait hesap kalıcı olarak silinmiştir. "
            "Yeniden erişim için sistem yöneticisiyle iletişime geçin."
        )
    user = User(
        email=email,
        password_hash=hash_password(payload.password, settings),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        department=payload.department,
        role=UserRole.USER.value,
        is_active=True,
        must_change_password=False,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if _is_email_unique_violation(exc):
            raise EmailAlreadyExistsError("Bu e-posta adresi zaten kayıtlı.") from exc
        raise
    session.refresh(user)
    return user


def authenticate_user(
    email: str,
    password: str,
    session: Session,
    settings: Settings,
) -> User | None:
    normalized_email = validate_allowed_email(email, settings.allowed_email_domains)
    user = session.scalar(select(User).where(User.email == normalized_email))

    password_hash = (
        user.password_hash
        if user is not None
        else dummy_password_hash(
            settings.password_scrypt_n,
            settings.password_scrypt_r,
            settings.password_scrypt_p,
        )
    )
    password_matches = verify_password(password, password_hash)
    if user is None:
        deleted_fingerprint = account_email_fingerprint(normalized_email, settings)
        if session.get(DeletedAccount, deleted_fingerprint) is not None:
            raise DeletedAccountError(
                "Bu hesap kalıcı olarak silinmiştir. Sistem yöneticisiyle iletişime geçin."
            )
        return None
    if not password_matches:
        return None
    if not user.is_active:
        raise InactiveAccountError(
            "Hesabınız pasif durumdadır. Yeniden etkinleştirilmesi için sistem "
            "yöneticisiyle iletişime geçin."
        )
    return user


def update_user_profile(
    user: User,
    changes: dict[str, object],
    session: Session,
    settings: Settings,
) -> User:
    normalized_changes = dict(changes)
    if "email" in normalized_changes:
        normalized_changes["email"] = validate_allowed_email(
            str(normalized_changes["email"]), settings.allowed_email_domains
        )
        if normalized_changes["email"] != user.email:
            deleted_fingerprint = account_email_fingerprint(
                str(normalized_changes["email"]), settings
            )
            if session.get(DeletedAccount, deleted_fingerprint) is not None:
                raise DeletedAccountError(
                    "Bu e-posta adresine ait hesap kalıcı olarak silinmiştir. "
                    "Farklı bir e-posta adresi kullanın."
                )
    changed_fields = [
        field for field, value in normalized_changes.items() if getattr(user, field) != value
    ]
    if not changed_fields:
        return user
    if settings.is_demo_account_protected(user.email):
        raise DemoAccountProtectedError(
            "Bu ortak demo hesabının profil bilgileri değiştirilemez."
        )

    previous_email = user.email
    for field in changed_fields:
        setattr(user, field, normalized_changes[field])
    user.updated_at = datetime.now(UTC).replace(tzinfo=None)
    details: dict[str, object] = {"changed_fields": sorted(changed_fields)}
    if "email" in changed_fields:
        details["previous_email"] = previous_email
        details["new_email"] = user.email
    record_audit_event(
        session,
        user,
        "USER_PROFILE_UPDATED",
        "USER",
        user.id,
        details,
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if _is_email_unique_violation(exc):
            raise EmailAlreadyExistsError("Bu e-posta adresi zaten kayıtlı.") from exc
        raise
    session.refresh(user)
    return user


def change_user_password(
    user: User,
    current_password: str,
    new_password: str,
    session: Session,
    settings: Settings,
) -> User:
    if settings.is_demo_account_protected(user.email):
        raise DemoAccountProtectedError(
            "Bu ortak demo hesabının şifresi değiştirilemez."
        )
    if not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError("Mevcut şifre hatalı.")
    if verify_password(new_password, user.password_hash):
        raise ValueError("Yeni şifre mevcut şifreden farklı olmalıdır.")
    user.password_hash = hash_password(new_password, settings)
    user.must_change_password = False
    session.commit()
    session.refresh(user)
    return user
