from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.main import create_app
from app.models.entities import AuditEvent, User
from app.models.enums import UserRole
from tests.test_tickets import (
    PASSWORD,
    create_ticket,
    csrf_headers,
    login,
    promote_to_it,
    register_user,
)

ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "YoneticiParola123"
TEMPORARY_PASSWORD = "GeciciParola123"


def create_admin() -> int:
    settings = get_settings()
    with get_session_factory()() as session:
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD, settings),
            first_name="Sistem",
            last_name="Yöneticisi",
            department="Yönetim",
            role=UserRole.ADMIN.value,
            is_active=True,
            must_change_password=False,
        )
        session.add(admin)
        session.commit()
        return admin.id


def login_admin(client: TestClient) -> None:
    client.cookies.clear()
    response = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200


def resolve_ticket_for_it(client: TestClient, ticket_id: int, it_id: int) -> None:
    promote_to_it(it_id)
    assert client.patch(
        f"/api/it/tickets/{ticket_id}/priority",
        json={"priority": "HIGH"},
        headers=csrf_headers(client),
    ).status_code == 200
    assert client.post(
        f"/api/it/tickets/{ticket_id}/assign-self",
        headers=csrf_headers(client),
    ).status_code == 200
    assert client.post(
        f"/api/it/tickets/{ticket_id}/resolve",
        json={"resolution_note": "Sorun kalıcı olarak giderildi."},
        headers=csrf_headers(client),
    ).status_code == 200


def test_admin_creates_it_and_temporary_password_must_be_changed() -> None:
    create_admin()
    with TestClient(create_app()) as client:
        login_admin(client)
        created = client.post(
            "/api/admin/users/it",
            json={
                "email": "destek@company.com",
                "temporary_password": TEMPORARY_PASSWORD,
                "first_name": "Destek",
                "last_name": "Uzmanı",
                "department": "Bilgi İşlem",
            },
            headers=csrf_headers(client),
        )
        dashboard = client.get("/api/admin/dashboard")
        users = client.get("/api/admin/users?role=IT")

        client.cookies.clear()
        logged_in = client.post(
            "/api/auth/login",
            json={"email": "destek@company.com", "password": TEMPORARY_PASSWORD},
        )
        blocked = client.get("/api/it/tickets")
        changed = client.post(
            "/api/users/me/password",
            json={
                "current_password": TEMPORARY_PASSWORD,
                "new_password": PASSWORD,
            },
            headers=csrf_headers(client),
        )
        allowed = client.get("/api/it/tickets")

    assert created.status_code == 201
    assert created.json()["role"] == UserRole.IT.value
    assert created.json()["must_change_password"] is True
    assert dashboard.json()["it_users"] == 1
    assert users.json()["total"] == 1
    assert logged_in.status_code == 200
    assert blocked.status_code == 403
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert allowed.status_code == 200


def test_admin_cannot_mutate_protected_demo_account(monkeypatch) -> None:
    protected_email = "demo.it@company.com"
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    monkeypatch.setenv("APP_DEMO_PROTECTED_EMAILS", f'["{protected_email}"]')
    get_settings.cache_clear()
    create_admin()

    with TestClient(create_app()) as client:
        login_admin(client)
        created = client.post(
            "/api/admin/users/it",
            json={
                "email": protected_email,
                "temporary_password": TEMPORARY_PASSWORD,
                "first_name": "Demo",
                "last_name": "Uzmanı",
                "department": "IT Destek",
            },
            headers=csrf_headers(client),
        )
        user_id = created.json()["id"]
        updated = client.patch(
            f"/api/admin/users/{user_id}",
            json={"first_name": "Değiştirilemez"},
            headers=csrf_headers(client),
        )
        deactivated = client.patch(
            f"/api/admin/users/{user_id}/status",
            json={"is_active": False, "reason": "Demo koruma testi."},
            headers=csrf_headers(client),
        )
        password_reset = client.post(
            f"/api/admin/users/{user_id}/temporary-password",
            json={
                "temporary_password": "YeniDemoParola123",
                "reason": "Demo koruma testi.",
            },
            headers=csrf_headers(client),
        )
        deleted = client.request(
            "DELETE",
            f"/api/admin/users/{user_id}",
            json={"confirmation_email": protected_email, "reason": "Demo koruma testi."},
            headers=csrf_headers(client),
        )

    assert created.status_code == 201
    assert {updated.status_code, deactivated.status_code, password_reset.status_code} == {409}
    assert deleted.status_code == 409


def test_admin_user_management_lifecycle_and_permanent_delete() -> None:
    create_admin()
    managed_email = "yonetilen.it@company.com"
    with TestClient(create_app()) as client:
        login_admin(client)
        created = client.post(
            "/api/admin/users/it",
            json={
                "email": managed_email,
                "temporary_password": TEMPORARY_PASSWORD,
                "first_name": "Eski",
                "last_name": "İsim",
                "department": "Bilgi İşlem",
            },
            headers=csrf_headers(client),
        )
        assert created.status_code == 201
        user_id = created.json()["id"]

        updated = client.patch(
            f"/api/admin/users/{user_id}",
            json={
                "first_name": "Yeni",
                "last_name": "İsim",
                "department": "Altyapı",
                "phone": None,
            },
            headers=csrf_headers(client),
        )
        reset_password = client.post(
            f"/api/admin/users/{user_id}/temporary-password",
            json={
                "temporary_password": "YenilenenParola123",
                "reason": "Kullanıcı talep etti.",
            },
            headers=csrf_headers(client),
        )
        deactivated = client.patch(
            f"/api/admin/users/{user_id}/status",
            json={"is_active": False, "reason": "Geçici erişim kapatma."},
            headers=csrf_headers(client),
        )
        activated = client.patch(
            f"/api/admin/users/{user_id}/status",
            json={"is_active": True, "reason": "Erişim yeniden açıldı."},
            headers=csrf_headers(client),
        )
        client.cookies.clear()
        profile_login = client.post(
            "/api/auth/login",
            json={"email": managed_email, "password": "YenilenenParola123"},
        )
        profile_update = client.patch(
            "/api/users/me",
            json={"phone": "+90 555 111 22 33"},
            headers=csrf_headers(client),
        )
        login_admin(client)
        wrong_confirmation = client.request(
            "DELETE",
            f"/api/admin/users/{user_id}",
            json={"confirmation_email": "yanlis@company.com", "reason": "Test hesabı."},
            headers=csrf_headers(client),
        )
        deleted = client.request(
            "DELETE",
            f"/api/admin/users/{user_id}",
            json={"confirmation_email": managed_email, "reason": "Test hesabı tamamlandı."},
            headers=csrf_headers(client),
        )

        with get_session_factory()() as session:
            stored_user = session.get(User, user_id)
            delete_event = session.query(AuditEvent).filter(
                AuditEvent.action == "USER_PERMANENTLY_DELETED",
                AuditEvent.entity_id == user_id,
            ).one_or_none()

    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Yeni"
    assert updated.json()["department"] == "Altyapı"
    assert reset_password.status_code == 200
    assert reset_password.json()["must_change_password"] is True
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    assert profile_login.status_code == 200
    assert profile_update.status_code == 200
    assert wrong_confirmation.status_code == 409
    assert deleted.status_code == 204
    assert stored_user is None
    assert delete_event is not None


def test_permanent_delete_preserves_business_history() -> None:
    create_admin()
    with TestClient(create_app()) as client:
        user = register_user(client)
        create_ticket(client)
        login_admin(client)
        blocked = client.request(
            "DELETE",
            f"/api/admin/users/{user['id']}",
            json={
                "confirmation_email": user["email"],
                "reason": "Geçmişi olan hesap silme denemesi.",
            },
            headers=csrf_headers(client),
        )

        with get_session_factory()() as session:
            stored_user = session.get(User, user["id"])

    assert blocked.status_code == 409
    assert "iş geçmişine bağlı" in blocked.json()["detail"]
    assert stored_user is not None


def test_inactive_and_deleted_accounts_receive_clear_login_status() -> None:
    create_admin()
    managed_email = "durum.test@company.com"
    with TestClient(create_app()) as client:
        login_admin(client)
        created = client.post(
            "/api/admin/users/it",
            json={
                "email": managed_email,
                "temporary_password": TEMPORARY_PASSWORD,
                "first_name": "Durum",
                "last_name": "Test",
                "department": "Bilgi İşlem",
            },
            headers=csrf_headers(client),
        )
        user_id = created.json()["id"]
        deactivated = client.patch(
            f"/api/admin/users/{user_id}/status",
            json={"is_active": False, "reason": "Hesap geçici olarak kapatıldı."},
            headers=csrf_headers(client),
        )

        client.cookies.clear()
        inactive_login = client.post(
            "/api/auth/login",
            json={"email": managed_email, "password": TEMPORARY_PASSWORD},
        )

        login_admin(client)
        deleted = client.request(
            "DELETE",
            f"/api/admin/users/{user_id}",
            json={"confirmation_email": managed_email, "reason": "Test hesabı kapatıldı."},
            headers=csrf_headers(client),
        )

        client.cookies.clear()
        deleted_login = client.post(
            "/api/auth/login",
            json={"email": managed_email, "password": TEMPORARY_PASSWORD},
        )
        reregister = client.post(
            "/api/auth/register",
            json={
                "email": managed_email,
                "password": PASSWORD,
                "first_name": "Yeniden",
                "last_name": "Kayıt",
                "department": "Bilgi İşlem",
            },
        )

    assert created.status_code == 201
    assert deactivated.status_code == 200
    assert inactive_login.status_code == 403
    assert "pasif" in inactive_login.json()["detail"]
    assert deleted.status_code == 204
    assert deleted_login.status_code == 410
    assert "kalıcı olarak silinmiştir" in deleted_login.json()["detail"]
    assert reregister.status_code == 409
    assert "kalıcı olarak silinmiştir" in reregister.json()["detail"]


def test_ticket_soft_delete_is_hidden_audited_and_admin_can_restore() -> None:
    create_admin()
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        deleted = client.request(
            "DELETE",
            f"/api/tickets/{ticket['id']}",
            json={"reason": "Talep yanlışlıkla açıldı."},
            headers=csrf_headers(client),
        )
        hidden = client.get(f"/api/tickets/{ticket['id']}")
        own_list = client.get("/api/tickets")

        login_admin(client)
        recycle_bin = client.get("/api/admin/tickets?state=deleted")
        restored = client.post(
            f"/api/admin/tickets/{ticket['id']}/restore",
            headers=csrf_headers(client),
        )

        login(client, "ayse@company.com")
        visible_again = client.get(f"/api/tickets/{ticket['id']}")
        with get_session_factory()() as session:
            actions = session.scalars(
                session.query(AuditEvent.action)
                .filter(AuditEvent.entity_id == ticket["id"])
                .statement
            ).all()

    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None
    assert hidden.status_code == 404
    assert own_list.json()["total"] == 0
    assert recycle_bin.json()["total"] == 1
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None
    assert visible_again.status_code == 200
    assert "TICKET_DELETED" in actions
    assert "TICKET_RESTORED" in actions


def test_admin_assigns_ticket_to_it_while_self_assignment_still_works() -> None:
    create_admin()
    with TestClient(create_app()) as client:
        register_user(client)
        assigned_ticket = create_ticket(client, subject="Admin tarafından atanacak")
        self_assigned_ticket = create_ticket(client, subject="IT kendisi alacak")

        client.cookies.clear()
        it_user = register_user(
            client,
            email="atama.it@company.com",
            first_name="Atama",
            last_name="Uzmanı",
            department="Bilgi İşlem",
        )
        promote_to_it(int(it_user["id"]))

        login_admin(client)
        assigned = client.patch(
            f"/api/admin/tickets/{assigned_ticket['id']}/assignee",
            json={"it_user_id": it_user["id"]},
            headers=csrf_headers(client),
        )
        duplicate_assignment = client.patch(
            f"/api/admin/tickets/{assigned_ticket['id']}/assignee",
            json={"it_user_id": it_user["id"]},
            headers=csrf_headers(client),
        )
        admin_pool = client.get("/api/admin/tickets?state=active")

        login(client, "ayse@company.com")
        requester_view = client.get(f"/api/tickets/{assigned_ticket['id']}")

        login(client, "atama.it@company.com")
        mine_before_self_assignment = client.get("/api/it/tickets?view=mine")
        self_assigned = client.post(
            f"/api/it/tickets/{self_assigned_ticket['id']}/assign-self",
            headers=csrf_headers(client),
        )
        mine_after_self_assignment = client.get("/api/it/tickets?view=mine")

        with get_session_factory()() as session:
            audit_event = session.query(AuditEvent).filter(
                AuditEvent.action == "TICKET_ASSIGNED_BY_ADMIN",
                AuditEvent.entity_id == assigned_ticket["id"],
            ).one_or_none()

    assert assigned.status_code == 200
    assert assigned.json()["assigned_to"] == it_user["id"]
    assert assigned.json()["assignee"]["email"] == "atama.it@company.com"
    assert duplicate_assignment.status_code == 409
    pooled_ticket = next(
        item for item in admin_pool.json()["items"] if item["id"] == assigned_ticket["id"]
    )
    assert pooled_ticket["assignee"]["first_name"] == "Atama"
    assert requester_view.status_code == 200
    assert "assignee" not in requester_view.json()
    assert mine_before_self_assignment.json()["total"] == 1
    assert self_assigned.status_code == 200
    assert mine_after_self_assignment.json()["total"] == 2
    assert audit_event is not None


def test_rating_remains_available_while_removed_routes_return_not_found() -> None:
    create_admin()
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)

        client.cookies.clear()
        it_user = register_user(
            client,
            email="it@company.com",
            first_name="Bilgi",
            last_name="İşlem",
            department="Bilgi İşlem",
        )
        resolve_ticket_for_it(client, int(ticket["id"]), int(it_user["id"]))

        login(client, "ayse@company.com")
        rated = client.put(
            f"/api/tickets/{ticket['id']}/rating",
            json={"score": 5, "comment": "Hızlı ve kalıcı çözüm."},
            headers=csrf_headers(client),
        )
        rating = client.get(f"/api/tickets/{ticket['id']}/rating")

        login(client, "it@company.com")
        notifications = client.get("/api/notifications").json()["items"]

        login(client, "ayse@company.com")
        updated = client.put(
            f"/api/tickets/{ticket['id']}/rating",
            json={"score": 4},
            headers=csrf_headers(client),
        )
        removed_user_route = client.get("/api/rewards/current")

        login_admin(client)
        removed_admin_route = client.get("/api/admin/rewards")

    assert rated.status_code == 200
    assert rating.json()["score"] == 5
    assert any(item["type"] == "TICKET_RATED" for item in notifications)
    assert updated.status_code == 200
    assert updated.json()["score"] == 4
    assert removed_user_route.status_code == 404
    assert removed_admin_route.status_code == 404
