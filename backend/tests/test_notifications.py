from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.main import create_app
from app.models.entities import Notification
from app.models.enums import EmailStatus, NotificationType
from tests.test_tickets import (
    create_ticket,
    csrf_headers,
    login,
    promote_to_it,
    register_user,
)


def test_new_ticket_notification_is_visible_only_to_active_it() -> None:
    with TestClient(create_app()) as client:
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))

        client.cookies.clear()
        register_user(client)
        create_ticket(client)
        user_notifications = client.get("/api/notifications")

        login(client, "it@company.com")
        it_notifications = client.get("/api/notifications")
        notification = it_notifications.json()["items"][0]
        marked = client.patch(
            f"/api/notifications/{notification['id']}/read",
            headers=csrf_headers(client),
        )

        login(client, "ayse@company.com")
        hidden = client.patch(
            f"/api/notifications/{notification['id']}/read",
            headers=csrf_headers(client),
        )

    assert user_notifications.json()["total"] == 0
    assert it_notifications.json()["total"] == 1
    assert notification["type"] == NotificationType.NEW_TICKET.value
    assert notification["email_status"] == EmailStatus.SKIPPED.value
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert marked.json()["read_at"].endswith("Z")
    assert hidden.status_code == 404


def test_resolution_creates_owner_notification() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        ticket_id = int(ticket["id"])

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        assert client.patch(
            f"/api/it/tickets/{ticket_id}/priority",
            json={"priority": "HIGH"},
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket_id}/assign-self",
            headers=csrf_headers(client),
        ).status_code == 200
        resolved = client.post(
            f"/api/it/tickets/{ticket_id}/resolve",
            json={"resolution_note": "Ağ ayarları düzeltildi."},
            headers=csrf_headers(client),
        )

        login(client, "ayse@company.com")
        notifications = client.get("/api/notifications")

    assert resolved.status_code == 200
    assert notifications.json()["total"] == 1
    assert notifications.json()["items"][0]["type"] == NotificationType.TICKET_RESOLVED.value


def test_smtp_failure_is_recorded_without_rolling_back_resolution(monkeypatch) -> None:
    monkeypatch.setenv("APP_SMTP_HOST", "smtp.internal")
    monkeypatch.setenv("APP_MAIL_FROM", "tickets@company.com")
    get_settings.cache_clear()

    def fail_email(*_args, **_kwargs) -> None:
        raise OSError("SMTP unavailable")

    monkeypatch.setattr("app.services.notifications._send_email", fail_email)
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        ticket_id = int(ticket["id"])

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        assert client.patch(
            f"/api/it/tickets/{ticket_id}/priority",
            json={"priority": "CRITICAL"},
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket_id}/assign-self",
            headers=csrf_headers(client),
        ).status_code == 200
        resolved = client.post(
            f"/api/it/tickets/{ticket_id}/resolve",
            json={"resolution_note": "Servis yeniden başlatıldı."},
            headers=csrf_headers(client),
        )

        login(client, "ayse@company.com")
        ticket_detail = client.get(f"/api/tickets/{ticket_id}")

        with get_session_factory()() as session:
            notification = session.query(Notification).filter_by(
                ticket_id=ticket_id,
                type=NotificationType.TICKET_RESOLVED.value,
            ).one()
            email_status = notification.email_status
            attempt_count = notification.email_attempt_count
            last_error = notification.email_last_error

    assert resolved.status_code == 200
    assert ticket_detail.json()["is_resolved"] is True
    assert email_status == EmailStatus.FAILED.value
    assert attempt_count == 1
    assert "SMTP unavailable" in last_error


def test_successful_smtp_delivery_is_recorded(monkeypatch) -> None:
    monkeypatch.setenv("APP_SMTP_HOST", "smtp.internal")
    monkeypatch.setenv("APP_MAIL_FROM", "tickets@company.com")
    get_settings.cache_clear()
    delivered_to: list[str] = []

    def record_email(notification, _settings) -> None:
        delivered_to.append(notification.email_recipient)

    monkeypatch.setattr("app.services.notifications._send_email", record_email)
    with TestClient(create_app()) as client:
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))

        client.cookies.clear()
        register_user(client)
        create_ticket(client)

        login(client, "it@company.com")
        notification = client.get("/api/notifications").json()["items"][0]

    assert delivered_to == ["it@company.com"]
    assert notification["email_status"] == EmailStatus.SENT.value


def test_email_delivery_flag_skips_smtp_but_keeps_in_app_notification(monkeypatch) -> None:
    monkeypatch.setenv("APP_EMAIL_DELIVERY_ENABLED", "false")
    monkeypatch.setenv("APP_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("APP_MAIL_FROM", "tickets@company.com")
    get_settings.cache_clear()
    delivered_to: list[str] = []

    def record_email(notification, _settings) -> None:
        delivered_to.append(notification.email_recipient)

    monkeypatch.setattr("app.services.notifications._send_email", record_email)
    with TestClient(create_app()) as client:
        it_user = register_user(client, email="it@company.com", department="IT Destek")
        promote_to_it(int(it_user["id"]))

        client.cookies.clear()
        register_user(client)
        create_ticket(client)

        login(client, "it@company.com")
        notification = client.get("/api/notifications").json()["items"][0]

    assert delivered_to == []
    assert notification["email_status"] == EmailStatus.SKIPPED.value
