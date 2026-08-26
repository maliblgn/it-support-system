from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from tests.test_tickets import (
    create_ticket,
    csrf_headers,
    login,
    promote_to_it,
    register_user,
)

PNG_CONTENT = b"\x89PNG\r\n\x1a\n" + b"test-image-content"
PDF_CONTENT = b"%PDF-1.7\n% test pdf\n%%EOF"


def configure_upload_root(monkeypatch: object, tmp_path: Path, **settings: str) -> None:
    monkeypatch.setenv("APP_UPLOAD_ROOT", str(tmp_path))
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()


def upload(
    client: TestClient,
    ticket_id: int,
    filename: str,
    content: bytes,
    content_type: str,
):
    return client.post(
        f"/api/tickets/{ticket_id}/attachments",
        files={"file": (filename, content, content_type)},
        headers=csrf_headers(client),
    )


def test_valid_attachment_is_stored_listed_and_authorized_for_download(
    monkeypatch, tmp_path: Path
) -> None:
    configure_upload_root(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        response = upload(client, int(ticket["id"]), "ekran.png", PNG_CONTENT, "image/png")
        attachment = response.json()
        detail = client.get(f"/api/tickets/{ticket['id']}")
        downloaded = client.get(
            f"/api/tickets/{ticket['id']}/attachments/{attachment['id']}"
        )

    stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert response.status_code == 201
    assert attachment["original_file_name"] == "ekran.png"
    assert "stored_file_name" not in attachment
    assert "storage_key" not in attachment
    assert len(detail.json()["attachments"]) == 1
    assert downloaded.status_code == 200
    assert downloaded.content == PNG_CONTENT
    assert len(stored_files) == 1
    assert stored_files[0].name != "ekran.png"


def test_attachment_rejects_forged_type_extension_and_path_traversal(
    monkeypatch, tmp_path: Path
) -> None:
    configure_upload_root(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        ticket_id = int(ticket["id"])

        forged_signature = upload(client, ticket_id, "fake.png", b"not-a-png", "image/png")
        mismatched_extension = upload(
            client,
            ticket_id,
            "document.pdf",
            PNG_CONTENT,
            "image/png",
        )
        traversal = upload(
            client,
            ticket_id,
            "../outside.png",
            PNG_CONTENT,
            "image/png",
        )
        unsupported = upload(
            client,
            ticket_id,
            "payload.exe",
            b"MZ executable",
            "application/octet-stream",
        )

    assert forged_signature.status_code == 422
    assert mismatched_extension.status_code == 422
    assert traversal.status_code == 422
    assert unsupported.status_code == 422
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


def test_attachment_size_and_count_limits_are_enforced(monkeypatch, tmp_path: Path) -> None:
    configure_upload_root(
        monkeypatch,
        tmp_path,
        APP_MAX_ATTACHMENT_SIZE_MB="1",
        APP_MAX_ATTACHMENTS_PER_TICKET="1",
    )
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        ticket_id = int(ticket["id"])

        oversized = upload(
            client,
            ticket_id,
            "large.pdf",
            b"%PDF-" + b"x" * (1024 * 1024),
            "application/pdf",
        )
        first = upload(client, ticket_id, "first.pdf", PDF_CONTENT, "application/pdf")
        second = upload(client, ticket_id, "second.pdf", PDF_CONTENT, "application/pdf")

    assert oversized.status_code == 422
    assert first.status_code == 201
    assert second.status_code == 409
    assert len([path for path in tmp_path.rglob("*") if path.is_file()]) == 1


def test_foreign_user_cannot_download_or_delete_attachment(monkeypatch, tmp_path: Path) -> None:
    configure_upload_root(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        attachment = upload(
            client,
            int(ticket["id"]),
            "evidence.pdf",
            PDF_CONTENT,
            "application/pdf",
        ).json()

        client.cookies.clear()
        register_user(client, email="other@company.com", first_name="Başka")
        download = client.get(
            f"/api/tickets/{ticket['id']}/attachments/{attachment['id']}"
        )
        deletion = client.delete(
            f"/api/tickets/{ticket['id']}/attachments/{attachment['id']}",
            headers=csrf_headers(client),
        )

    assert download.status_code == 404
    assert deletion.status_code == 404


def test_owner_can_delete_unresolved_attachment_and_file(monkeypatch, tmp_path: Path) -> None:
    configure_upload_root(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        attachment = upload(
            client,
            int(ticket["id"]),
            "remove.pdf",
            PDF_CONTENT,
            "application/pdf",
        ).json()
        deletion = client.delete(
            f"/api/tickets/{ticket['id']}/attachments/{attachment['id']}",
            headers=csrf_headers(client),
        )
        missing = client.get(
            f"/api/tickets/{ticket['id']}/attachments/{attachment['id']}"
        )

    assert deletion.status_code == 204
    assert missing.status_code == 404
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


def test_resolved_ticket_attachments_are_read_only(monkeypatch, tmp_path: Path) -> None:
    configure_upload_root(monkeypatch, tmp_path)
    with TestClient(create_app()) as client:
        register_user(client)
        ticket = create_ticket(client)
        ticket_id = int(ticket["id"])
        attachment = upload(
            client,
            ticket_id,
            "locked.pdf",
            PDF_CONTENT,
            "application/pdf",
        ).json()

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        it_download = client.get(
            f"/api/tickets/{ticket_id}/attachments/{attachment['id']}"
        )
        it_delete = client.delete(
            f"/api/tickets/{ticket_id}/attachments/{attachment['id']}",
            headers=csrf_headers(client),
        )
        assert client.patch(
            f"/api/it/tickets/{ticket_id}/priority",
            json={"priority": "NORMAL"},
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket_id}/assign-self",
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{ticket_id}/resolve",
            json={"resolution_note": "Tamamlandı."},
            headers=csrf_headers(client),
        ).status_code == 200

        login(client, "ayse@company.com")
        deletion = client.delete(
            f"/api/tickets/{ticket_id}/attachments/{attachment['id']}",
            headers=csrf_headers(client),
        )
        new_upload = upload(client, ticket_id, "new.pdf", PDF_CONTENT, "application/pdf")

    assert deletion.status_code == 409
    assert new_upload.status_code == 409
    assert it_download.status_code == 200
    assert it_download.content == PDF_CONTENT
    assert it_delete.status_code == 404
