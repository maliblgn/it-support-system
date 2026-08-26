from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.reports import excel_local_datetime, priority_label
from tests.test_tickets import (
    create_ticket,
    csrf_headers,
    promote_to_it,
    register_user,
)


def test_report_summary_and_excel_export_require_it_role() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        forbidden_summary = client.get("/api/it/reports/summary")
        forbidden_export = client.get("/api/it/reports/export.xlsx")

    assert forbidden_summary.status_code == 403
    assert forbidden_export.status_code == 403


def test_report_summary_matches_ticket_workflow_and_custom_validation() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        first = create_ticket(client, subject="Yazıcı")
        create_ticket(client, subject="VPN")

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        assert client.patch(
            f"/api/it/tickets/{first['id']}/priority",
            json={"priority": "NORMAL"},
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{first['id']}/assign-self",
            headers=csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/api/it/tickets/{first['id']}/resolve",
            json={"resolution_note": "Çözüldü."},
            headers=csrf_headers(client),
        ).status_code == 200

        summary = client.get("/api/it/reports/summary?period=month")
        invalid_custom = client.get("/api/it/reports/summary?period=custom")

    assert summary.status_code == 200
    assert summary.json()["total"] == 2
    assert summary.json()["resolved"] == 1
    assert summary.json()["could_not_resolve"] == 0
    assert summary.json()["unresolved"] == 1
    assert summary.json()["average_resolution_minutes"] is not None
    assert summary.json()["departments"] == [{"department": "Finans", "count": 2}]
    assert invalid_custom.status_code == 422


def test_excel_export_is_valid_and_prevents_formula_injection() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        create_ticket(client, subject='=HYPERLINK("https://invalid.example","click")')

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        response = client.get("/api/it/reports/export.xlsx?period=month")

    assert response.status_code == 200
    assert response.content.startswith(b"PK")
    assert "ticket-report-" in response.headers["content-disposition"]
    with ZipFile(BytesIO(response.content)) as archive:
        worksheet_xml = archive.read("xl/worksheets/sheet2.xml")
        shared_strings = archive.read("xl/sharedStrings.xml")
        workbook_xml = archive.read("xl/workbook.xml")
    assert b"<f>" not in worksheet_xml
    assert b"HYPERLINK" in shared_strings
    assert "Özet".encode() in workbook_xml
    assert "Ticket Detayı".encode() in workbook_xml
    assert "Tarih aralığı (İstanbul)".encode() in shared_strings


def test_excel_uses_istanbul_time_and_turkish_priority_labels() -> None:
    assert excel_local_datetime(datetime(2026, 8, 24, 9, 44)) == datetime(
        2026, 8, 24, 12, 44
    )
    assert priority_label("HIGH") == "Yüksek"
    assert priority_label(None) == "Belirlenmedi"
