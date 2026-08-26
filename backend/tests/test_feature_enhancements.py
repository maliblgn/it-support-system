from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import create_app
from app.models.entities import User
from app.models.enums import UserRole
from tests.test_tickets import (
    create_ticket,
    csrf_headers,
    login,
    promote_to_it,
    register_user,
)


def _set_role(user_id: int, role: UserRole) -> None:
    with get_session_factory()() as session:
        user = session.get(User, user_id)
        assert user is not None
        user.role = role.value
        session.commit()


def test_advanced_ticket_filters_tags_watchers_history_and_dashboard() -> None:
    with TestClient(create_app()) as client:
        owner = register_user(client)
        ticket = create_ticket(
            client,
            subject="VPN bağlantısı kesiliyor",
            description="Uzak bağlantı her on dakikada kopuyor.",
        )
        create_ticket(client, subject="Yazıcı toner talebi")

        client.cookies.clear()
        it_user = register_user(
            client,
            email="it@company.com",
            first_name="Deniz",
            last_name="Teknik",
            department="Bilgi İşlem",
        )
        promote_to_it(int(it_user["id"]))

        priority = client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "HIGH"},
            headers=csrf_headers(client),
        )
        assignment = client.post(
            f"/api/it/tickets/{ticket['id']}/assign-self",
            headers=csrf_headers(client),
        )
        tag = client.post(
            "/api/it/tags",
            json={"name": "Ağ", "color": "#2255AA"},
            headers=csrf_headers(client),
        )
        tagged = client.post(
            f"/api/it/tickets/{ticket['id']}/tags/{tag.json()['id']}",
            headers=csrf_headers(client),
        )
        watched = client.post(
            f"/api/it/tickets/{ticket['id']}/watch",
            headers=csrf_headers(client),
        )
        filtered = client.get(
            "/api/it/tickets",
            params={
                "search": "on dakikada",
                "status": "open",
                "priority": "HIGH",
                "department": "Finans",
                "owner": owner["email"],
                "assignee_id": it_user["id"],
                "tag_id": tag.json()["id"],
            },
        )
        options = client.get("/api/it/tickets/filter-options")
        history = client.get(f"/api/it/tickets/{ticket['id']}/history")
        dashboard = client.get("/api/it/reports/dashboard")

        assert priority.status_code == 200
        assert assignment.status_code == 200
        assert tag.status_code == 201
        assert tagged.status_code == 200
        assert tagged.json()["tags"][0]["name"] == "Ağ"
        assert watched.status_code == 200
        assert watched.json()["watchers"][0]["id"] == it_user["id"]
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1
        assert filtered.json()["items"][0]["id"] == ticket["id"]
        assert options.status_code == 200
        assert "Finans" in options.json()["departments"]
        assert options.json()["tags"][0]["name"] == "Ağ"
        actions = {item["action"] for item in history.json()}
        assert {
            "TICKET_CREATED",
            "TICKET_PRIORITY_CHANGED",
            "TICKET_ASSIGNED_SELF",
            "TICKET_TAG_ADDED",
            "TICKET_WATCH_STARTED",
        } <= actions
        assert dashboard.status_code == 200
        assert dashboard.json()["mine"] == 1
        assert dashboard.json()["high_priority_open"] == 1


def test_user_server_filters_reports_and_admin_canned_responses() -> None:
    with TestClient(create_app()) as client:
        user = register_user(client)
        ticket = create_ticket(client, subject="E-posta erişim problemi")
        create_ticket(client, subject="Yeni ekran talebi")

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        assert client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "NORMAL"},
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket['id']}/assign-self",
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket['id']}/resolve",
            json={"resolution_note": "Hesap ayarları yenilendi.", "outcome": "RESOLVED"},
            headers=csrf_headers(client),
        ).status_code == 200

        report = client.get("/api/it/reports/summary?period=year")
        assert report.status_code == 200
        payload = report.json()
        assert payload["fastest_resolution_minutes"] is not None
        assert payload["priorities"]
        assert payload["it_performance"][0]["resolved"] == 1
        assert payload["time_series"]

        login(client, str(user["email"]))
        resolved = client.get(
            "/api/tickets",
            params={"search": "erişim", "status": "resolved", "priority": "NORMAL"},
        )
        open_tickets = client.get("/api/tickets", params={"status": "open"})
        assert resolved.status_code == 200
        assert resolved.json()["total"] == 1
        assert resolved.json()["items"][0]["id"] == ticket["id"]
        assert open_tickets.json()["total"] == 1

        _set_role(int(it_user["id"]), UserRole.ADMIN)
        login(client, str(it_user["email"]))
        created = client.post(
            "/api/admin/canned-responses",
            json={"title": "Ağ ayarlarını yenile", "content": "Ağ profili yeniden oluşturuldu."},
            headers=csrf_headers(client),
        )
        assert created.status_code == 201
        updated = client.patch(
            f"/api/admin/canned-responses/{created.json()['id']}",
            json={"title": "Ağ profilini yenile"},
            headers=csrf_headers(client),
        )
        assert updated.status_code == 200
        assert updated.json()["title"] == "Ağ profilini yenile"
        assert client.delete(
            f"/api/admin/canned-responses/{created.json()['id']}",
            headers=csrf_headers(client),
        ).status_code == 204
        listed = client.get("/api/admin/canned-responses")
        assert listed.status_code == 200
        assert listed.json()[0]["is_active"] is False
