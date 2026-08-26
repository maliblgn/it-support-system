import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password, validate_allowed_email
from app.db.session import get_session_factory
from app.models.entities import User
from app.models.enums import UserRole
from app.services.audit import record_audit_event


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="İlk yönetici hesabını güvenli biçimde oluşturur."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--department", default="Yönetim")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    email = validate_allowed_email(args.email, settings.allowed_email_domains)
    password = getpass("İlk yönetici hesabı şifresi: ")
    confirmation = getpass("Şifreyi tekrar girin: ")
    if password != confirmation:
        raise SystemExit("Şifreler eşleşmiyor.")

    session = get_session_factory()()
    try:
        if session.scalar(select(User.id).where(User.email == email)) is not None:
            raise SystemExit("Bu e-posta adresi zaten kayıtlı.")
        user = User(
            email=email,
            password_hash=hash_password(password, settings),
            first_name=args.first_name.strip(),
            last_name=args.last_name.strip(),
            department=args.department.strip(),
            role=UserRole.ADMIN.value,
            is_active=True,
            must_change_password=False,
        )
        session.add(user)
        session.flush()
        record_audit_event(
            session,
            None,
            "INITIAL_ADMIN_CREATED",
            "USER",
            user.id,
            {"email": user.email},
        )
        session.commit()
    finally:
        session.close()
    print(f"Yönetici hesabı oluşturuldu: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
