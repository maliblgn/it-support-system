from sqlalchemy import select

from app.cli.seed_demo import main as seed_demo_accounts
from app.core.config import get_settings
from app.core.security import verify_password
from app.db.session import get_session_factory
from app.models.entities import User
from app.models.enums import UserRole


def test_demo_seed_creates_protected_role_accounts_idempotently(monkeypatch) -> None:
    password = "DemoHesapParola123"
    emails = {
        UserRole.USER: "demo.user@company.com",
        UserRole.IT: "demo.it@company.com",
        UserRole.ADMIN: "demo.admin@company.com",
    }
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    monkeypatch.setenv("APP_DEMO_PROTECTED_EMAILS", str(list(emails.values())).replace("'", '"'))
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", password)
    get_settings.cache_clear()

    assert seed_demo_accounts() == 0
    assert seed_demo_accounts() == 0

    with get_session_factory()() as session:
        users = session.scalars(select(User).order_by(User.email)).all()

    assert len(users) == 3
    assert {user.email: user.role for user in users} == {
        email: role.value for role, email in emails.items()
    }
    assert all(user.is_active for user in users)
    assert all(not user.must_change_password for user in users)
    assert all(verify_password(password, user.password_hash) for user in users)
    assert all(get_settings().is_demo_account_protected(user.email) for user in users)
