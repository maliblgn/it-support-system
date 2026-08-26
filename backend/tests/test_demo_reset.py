from sqlalchemy import func, select

from app.cli.reset_demo import reset_demo_data
from app.cli.seed_demo import main as seed_demo_accounts
from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.session import get_session_factory
from app.models.entities import AuditEvent, CannedResponse, Tag, Ticket, User
from app.models.enums import UserRole


def test_demo_reset_restores_accounts_and_baseline_data(monkeypatch, tmp_path) -> None:
    password = "DemoHesapParola123"
    protected_emails = [
        "demo.user@company.com",
        "demo.it@company.com",
        "demo.admin@company.com",
    ]
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    (upload_root / "eski-dosya.pdf").write_bytes(b"demo")

    monkeypatch.setenv("APP_DEMO_MODE", "true")
    monkeypatch.setenv("APP_DEMO_PROTECTED_EMAILS", str(protected_emails).replace("'", '"'))
    monkeypatch.setenv("APP_UPLOAD_ROOT", str(upload_root))
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", password)
    get_settings.cache_clear()
    assert seed_demo_accounts() == 0

    settings = get_settings()
    with get_session_factory()() as session:
        admin = session.scalar(select(User).where(User.role == UserRole.ADMIN.value))
        assert admin is not None
        admin.first_name = "Değişmiş"
        admin.is_active = False
        admin.password_hash = hash_password("FarkliParola456", settings)
        session.add(
            User(
                email="visitor@company.com",
                password_hash=hash_password("ZiyaretciParola123", settings),
                first_name="Demo",
                last_name="Ziyaretçi",
                department="Test",
                role=UserRole.USER.value,
                is_active=True,
                must_change_password=False,
            )
        )
        session.commit()

    first_result = reset_demo_data(settings)
    second_result = reset_demo_data(settings)

    with get_session_factory()() as session:
        users = session.scalars(select(User).order_by(User.email)).all()
        tickets = session.scalars(select(Ticket).order_by(Ticket.ticket_number)).all()
        tag_count = session.scalar(select(func.count(Tag.id)))
        canned_count = session.scalar(select(func.count(CannedResponse.id)))
        reset_events = session.scalars(
            select(AuditEvent).where(AuditEvent.action == "DEMO_RESET_COMPLETED")
        ).all()

    assert first_result.removed_users == 1
    assert second_result.removed_users == 0
    assert first_result.baseline_tickets == second_result.baseline_tickets == 4
    assert {user.email for user in users} == set(protected_emails)
    assert all(user.is_active for user in users)
    assert all(verify_password(password, user.password_hash) for user in users)
    assert next(user for user in users if user.role == UserRole.ADMIN.value).first_name == "Demo"
    assert [ticket.ticket_number for ticket in tickets] == [
        "IT-000001",
        "IT-000002",
        "IT-000003",
        "IT-000004",
    ]
    assert {ticket.resolution_outcome for ticket in tickets if ticket.is_resolved} == {
        "RESOLVED",
        "UNRESOLVED",
    }
    assert tag_count == 2
    assert canned_count == 1
    assert len(reset_events) == 1
    assert list(upload_root.iterdir()) == []
