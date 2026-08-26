"""Ortak tanıtım ortamı için korunan USER, IT ve ADMIN hesaplarını oluşturur."""

import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password, validate_allowed_email
from app.db.session import get_session_factory
from app.models.entities import User
from app.models.enums import UserRole
from app.services.audit import record_audit_event


@dataclass(frozen=True, slots=True)
class DemoAccount:
    email: str
    first_name: str
    last_name: str
    department: str
    role: UserRole


def _environment_value(name: str, default: str | None = None) -> str:
    value = (os.environ.get(name) or default or "").strip()
    if not value:
        raise SystemExit(f"{name} tanımlanmalıdır.")
    return value


def load_demo_accounts(settings: Settings) -> list[DemoAccount]:
    domain = settings.allowed_email_domains[0]
    accounts = [
        DemoAccount(
            email=_environment_value("DEMO_USER_EMAIL", f"demo.user@{domain}"),
            first_name="Demo",
            last_name="Kullanıcı",
            department="Operasyon",
            role=UserRole.USER,
        ),
        DemoAccount(
            email=_environment_value("DEMO_IT_EMAIL", f"demo.it@{domain}"),
            first_name="Demo",
            last_name="IT Uzmanı",
            department="IT Destek",
            role=UserRole.IT,
        ),
        DemoAccount(
            email=_environment_value("DEMO_ADMIN_EMAIL", f"demo.admin@{domain}"),
            first_name="Demo",
            last_name="Yönetici",
            department="Yönetim",
            role=UserRole.ADMIN,
        ),
    ]

    normalized_accounts = [
        DemoAccount(
            email=validate_allowed_email(account.email, settings.allowed_email_domains),
            first_name=account.first_name,
            last_name=account.last_name,
            department=account.department,
            role=account.role,
        )
        for account in accounts
    ]
    missing_protection = [
        account.email
        for account in normalized_accounts
        if not settings.is_demo_account_protected(account.email)
    ]
    if missing_protection:
        raise SystemExit(
            "Demo hesaplarının tamamı APP_DEMO_PROTECTED_EMAILS içinde olmalıdır: "
            + ", ".join(missing_protection)
        )
    return normalized_accounts


def sync_demo_accounts(
    session: Session,
    settings: Settings,
    password: str,
    *,
    restore_existing: bool = False,
) -> tuple[list[User], int]:
    accounts = load_demo_accounts(settings)
    users: list[User] = []
    created_count = 0
    for account in accounts:
        existing = session.scalar(select(User).where(User.email == account.email))
        if existing is not None:
            if not restore_existing and existing.role != account.role.value:
                raise SystemExit(
                    f"{account.email} hesabı beklenen {account.role.value} rolünde değil."
                )
            if restore_existing:
                existing.password_hash = hash_password(password, settings)
                existing.first_name = account.first_name
                existing.last_name = account.last_name
                existing.phone = None
                existing.department = account.department
                existing.role = account.role.value
                existing.is_active = True
                existing.must_change_password = False
            users.append(existing)
            continue

        user = User(
            email=account.email,
            password_hash=hash_password(password, settings),
            first_name=account.first_name,
            last_name=account.last_name,
            phone=None,
            department=account.department,
            role=account.role.value,
            is_active=True,
            must_change_password=False,
        )
        session.add(user)
        session.flush()
        record_audit_event(
            session,
            None,
            "DEMO_ACCOUNT_CREATED",
            "USER",
            user.id,
            {"email": user.email, "role": user.role},
        )
        users.append(user)
        created_count += 1
    return users, created_count


def main() -> int:
    settings = get_settings()
    if not settings.demo_mode:
        raise SystemExit("Demo hesapları yalnızca APP_DEMO_MODE=true iken oluşturulabilir.")

    password = _environment_value("DEMO_ACCOUNT_PASSWORD")

    session = get_session_factory()()
    try:
        _, created_count = sync_demo_accounts(session, settings, password)
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Demo hesap hazırlığı tamamlandı; oluşturulan={created_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
