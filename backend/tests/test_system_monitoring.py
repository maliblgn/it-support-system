import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.system_monitoring import read_recent_logs
from tests.test_tickets import promote_to_it, register_user


def test_system_endpoints_require_it_role_and_return_health() -> None:
    with TestClient(create_app()) as client:
        register_user(client)
        forbidden = client.get("/api/it/system/overview")

        client.cookies.clear()
        it_user = register_user(client, email="it@company.com", department="Bilgi İşlem")
        promote_to_it(int(it_user["id"]))
        overview = client.get("/api/it/system/overview")
        logs = client.get("/api/it/system/logs?limit=20")

    assert forbidden.status_code == 403
    assert overview.status_code == 200
    assert overview.json()["database_status"] == "ok"
    assert overview.json()["upload_status"] == "ok"
    assert logs.status_code == 200
    assert logs.json() == {"items": [], "returned": 0}


def test_recent_logs_are_filtered_sorted_and_limited(tmp_path: Path) -> None:
    log_file = tmp_path / "application.jsonl"
    now = datetime.now(UTC)
    payloads = [
        {
            "timestamp": (now - timedelta(seconds=2)).isoformat(),
            "level": "INFO",
            "logger": "app.one",
            "message": "Eski bilgi",
        },
        {
            "timestamp": now.isoformat(),
            "level": "ERROR",
            "logger": "app.two",
            "message": "Yeni hata",
            "context": {"ticket_id": 3},
        },
    ]
    log_file.write_text("\n".join(json.dumps(item) for item in payloads), encoding="utf-8")
    settings = Settings(log_file=log_file)

    page = read_recent_logs(settings, level="ERROR", limit=1)

    assert page.returned == 1
    assert page.items[0].message == "Yeni hata"
    assert page.items[0].context == {"ticket_id": 3}
