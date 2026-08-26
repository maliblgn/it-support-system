from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import create_app
from app.models.entities import User
from app.models.enums import UserRole

PASSWORD = "GuvenliParola123"


def user_payload(
    email: str,
    first_name: str = "Ayşe",
    last_name: str = "Yılmaz",
    department: str = "Finans",
) -> dict[str, str]:
    return {
        "email": email,
        "password": PASSWORD,
        "first_name": first_name,
        "last_name": last_name,
        "department": department,
    }


def register_user(client: TestClient, **changes: str) -> dict[str, object]:
    payload = user_payload("ayse@company.com")
    payload.update(changes)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str) -> None:
    client.cookies.clear()
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200


def promote_to_it(user_id: int) -> None:
    with get_session_factory()() as session:
        user = session.get(User, user_id)
        assert user is not None
        user.role = UserRole.IT.value
        session.commit()


def csrf_headers(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies["it_ticket_csrf"]}


def create_ticket(
    client: TestClient,
    subject: str = "Yazıcı bağlantı sorunu",
    description: str = "Muhasebe yazıcısına bağlanamıyorum.",
) -> dict[str, object]:
    response = client.post(
        "/api/tickets",
        json={"subject": subject, "description": description},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    return response.json()


def test_ticket_creation_uses_session_owner_and_department_snapshot() -> None:
    with TestClient(create_app()) as client:
        user = register_user(client)
        injected = client.post(
            "/api/tickets",
            json={
                "subject": "Yetki denemesi",
                "description": "İstemci alanları kabul edilmemeli.",
                "user_id": 999,
                "priority": "CRITICAL",
            },
            headers=csrf_headers(client),
        )
        ticket = create_ticket(client)

    assert injected.status_code == 422
    assert ticket["ticket_number"] == "IT-000001"
    assert ticket["user"]["id"] == user["id"]
    assert ticket["department_snapshot"] == "Finans"
    assert ticket["priority"] is None
    assert ticket["assigned_to"] is None
    assert ticket["is_resolved"] is False
    assert ticket["resolution_outcome"] is None
    assert ticket["created_at"].endswith("Z")


def test_user_ticket_list_is_paginated_and_limited_to_owner() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        first = create_ticket(client, subject="Birinci")
        create_ticket(client, subject="İkinci")
        third = create_ticket(client, subject="Üçüncü")

        first_page = client.get("/api/tickets?page=1&page_size=2")
        second_page = client.get("/api/tickets?page=2&page_size=2")
        invalid_size = client.get("/api/tickets?page_size=101")

        client.cookies.clear()
        register_user(
            client,
            email="mehmet@company.com",
            first_name="Mehmet",
            last_name="Kaya",
            department="İnsan Kaynakları",
        )
        other_user_list = client.get("/api/tickets")
        hidden_detail = client.get(f"/api/tickets/{first['id']}")

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert first_page.json()["pages"] == 2
    assert first_page.json()["items"][0]["id"] == third["id"]
    assert second_page.json()["items"][0]["id"] == first["id"]
    assert invalid_size.status_code == 422
    assert other_user_list.json()["total"] == 0
    assert hidden_detail.status_code == 404


def test_user_can_edit_only_an_own_unresolved_ticket() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        updated = client.patch(
            f"/api/tickets/{ticket['id']}",
            json={"subject": "Güncellenmiş konu"},
            headers=csrf_headers(client),
        )
        null_subject = client.patch(
            f"/api/tickets/{ticket['id']}",
            json={"subject": None},
            headers=csrf_headers(client),
        )

        client.cookies.clear()
        register_user(client, email="baska@company.com", first_name="Başka")
        forbidden_update = client.patch(
            f"/api/tickets/{ticket['id']}",
            json={"description": "Yetkisiz değişiklik"},
            headers=csrf_headers(client),
        )

    assert updated.status_code == 200
    assert updated.json()["subject"] == "Güncellenmiş konu"
    assert null_subject.status_code == 422
    assert forbidden_update.status_code == 404


def test_regular_user_cannot_access_it_ticket_endpoints() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)

        listing = client.get("/api/it/tickets")
        priority = client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "HIGH"},
            headers=csrf_headers(client),
        )

    assert listing.status_code == 403
    assert priority.status_code == 403


def test_it_workflow_requires_priority_assignment_and_resolution_note() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)

        client.cookies.clear()
        it_user = register_user(
            client,
            email="it1@company.com",
            first_name="Bilgi",
            last_name="İşlem",
            department="Bilgi İşlem",
        )
        promote_to_it(int(it_user["id"]))

        resolve_before_setup = client.post(
            f"/api/it/tickets/{ticket['id']}/resolve",
            json={"resolution_note": "Çözüldü"},
            headers=csrf_headers(client),
        )
        invalid_priority = client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "URGENT"},
            headers=csrf_headers(client),
        )
        priority = client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "NORMAL"},
            headers=csrf_headers(client),
        )
        resolve_before_assignment = client.post(
            f"/api/it/tickets/{ticket['id']}/resolve",
            json={"resolution_note": "Çözüldü"},
            headers=csrf_headers(client),
        )
        assignment = client.post(
            f"/api/it/tickets/{ticket['id']}/assign-self",
            headers=csrf_headers(client),
        )
        empty_resolution = client.post(
            f"/api/it/tickets/{ticket['id']}/resolve",
            json={"resolution_note": "   "},
            headers=csrf_headers(client),
        )
        resolved = client.post(
            f"/api/it/tickets/{ticket['id']}/resolve",
            json={"resolution_note": "Yazıcı sürücüsü yeniden kuruldu."},
            headers=csrf_headers(client),
        )
        priority_after_resolution = client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "HIGH"},
            headers=csrf_headers(client),
        )

        login(client, "ayse@company.com")
        edit_after_resolution = client.patch(
            f"/api/tickets/{ticket['id']}",
            json={"subject": "Değiştirilemez"},
            headers=csrf_headers(client),
        )

    assert resolve_before_setup.status_code == 409
    assert invalid_priority.status_code == 422
    assert priority.status_code == 200
    assert resolve_before_assignment.status_code == 409
    assert assignment.status_code == 200
    assert assignment.json()["assigned_to"] == it_user["id"]
    assert empty_resolution.status_code == 422
    assert resolved.status_code == 200
    assert resolved.json()["is_resolved"] is True
    assert resolved.json()["resolution_outcome"] == "RESOLVED"
    assert resolved.json()["resolved_by"] == it_user["id"]
    assert priority_after_resolution.status_code == 409
    assert edit_after_resolution.status_code == 409


def test_it_can_close_ticket_as_unresolved_and_it_cannot_be_rated() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client, subject="Donanım değişimi gerekiyor")

        client.cookies.clear()
        it_user = register_user(
            client,
            email="it@company.com",
            first_name="Teknik",
            last_name="Uzman",
            department="Bilgi İşlem",
        )
        promote_to_it(int(it_user["id"]))
        assert client.patch(
            f"/api/it/tickets/{ticket['id']}/priority",
            json={"priority": "HIGH"},
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket['id']}/assign-self",
            headers=csrf_headers(client),
        ).status_code == 200
        result = client.post(
            f"/api/it/tickets/{ticket['id']}/resolve",
            json={
                "resolution_note": "Arızalı parça stokta olmadığı için çözülemedi.",
                "outcome": "UNRESOLVED",
            },
            headers=csrf_headers(client),
        )
        summary = client.get("/api/it/reports/summary?period=month")

        login(client, "ayse@company.com")
        owner_view = client.get(f"/api/tickets/{ticket['id']}")
        rating = client.put(
            f"/api/tickets/{ticket['id']}/rating",
            json={"score": 5},
            headers=csrf_headers(client),
        )
        notifications = client.get("/api/notifications").json()["items"]

    assert result.status_code == 200
    assert result.json()["is_resolved"] is True
    assert result.json()["resolution_outcome"] == "UNRESOLVED"
    assert owner_view.json()["resolution_outcome"] == "UNRESOLVED"
    assert rating.status_code == 409
    assert summary.status_code == 200
    assert summary.json()["resolved"] == 0
    assert summary.json()["could_not_resolve"] == 1
    assert summary.json()["unresolved"] == 0
    assert any(item["type"] == "TICKET_UNRESOLVED" for item in notifications)


def test_first_it_assignment_wins_and_filters_are_consistent() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client, subject="VPN erişim sorunu")

        client.cookies.clear()
        first_it = register_user(
            client,
            email="it1@company.com",
            first_name="Birinci",
            department="Bilgi İşlem",
        )
        promote_to_it(int(first_it["id"]))
        first_assignment = client.post(
            f"/api/it/tickets/{ticket['id']}/assign-self",
            headers=csrf_headers(client),
        )
        mine = client.get("/api/it/tickets?view=mine&search=VPN")
        unassigned = client.get("/api/it/tickets?view=unassigned")

        client.cookies.clear()
        second_it = register_user(
            client,
            email="it2@company.com",
            first_name="İkinci",
            department="Bilgi İşlem",
        )
        promote_to_it(int(second_it["id"]))
        second_assignment = client.post(
            f"/api/it/tickets/{ticket['id']}/assign-self",
            headers=csrf_headers(client),
        )

    assert first_assignment.status_code == 200
    assert mine.status_code == 200
    assert mine.json()["total"] == 1
    assert unassigned.json()["total"] == 0
    assert second_assignment.status_code == 409


def test_ticket_numbers_are_unique_and_sequential() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        first = create_ticket(client)
        second = create_ticket(client, subject="İkinci talep")

    assert first["ticket_number"] == "IT-000001"
    assert second["ticket_number"] == "IT-000002"
