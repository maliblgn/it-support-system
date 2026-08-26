import json
import logging
from pathlib import Path

from app.core.logging import JsonContextFormatter, SafeContextFormatter, configure_logging


def test_safe_context_formatter_includes_only_approved_fields() -> None:
    record = logging.LogRecord(
        name="app.services.tickets",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Ticket çözüldü.",
        args=(),
        exc_info=None,
    )
    record.ticket_id = 42
    record.it_user_id = 7
    record.password = "asla-loglanmamali"
    formatter = SafeContextFormatter("%(levelname)s %(message)s")

    output = formatter.format(record)

    assert output == "INFO Ticket çözüldü. it_user_id=7 ticket_id=42"
    assert "password" not in output
    assert "asla-loglanmamali" not in output


def test_json_logging_rotates_and_excludes_unapproved_fields(tmp_path: Path) -> None:
    log_file = tmp_path / "application.jsonl"
    configure_logging("INFO", log_file, log_max_bytes=1024 * 1024, log_backup_count=2)
    logger = logging.getLogger("app.test")

    logger.info(
        "Ticket oluşturuldu.",
        extra={
            "ticket_id": 12,
            "user_id": 4,
            "http_method": "POST",
            "status_code": 201,
            "password": "gizli",
        },
    )
    for handler in logging.getLogger().handlers:
        handler.flush()

    payload = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert payload["message"] == "Ticket oluşturuldu."
    assert payload["context"] == {
        "user_id": 4,
        "ticket_id": 12,
        "http_method": "POST",
        "status_code": 201,
    }
    assert "password" not in payload
    assert "gizli" not in log_file.read_text(encoding="utf-8")


def test_json_formatter_records_exception_type_without_traceback_details() -> None:
    formatter = JsonContextFormatter()
    try:
        raise RuntimeError("iç bağlantı ayrıntısı")
    except RuntimeError:
        record = logging.getLogger("app.test").makeRecord(
            "app.test",
            logging.ERROR,
            __file__,
            1,
            "İşlem başarısız.",
            (),
            exc_info=__import__("sys").exc_info(),
        )

    payload = json.loads(formatter.format(record))
    assert payload["exception_type"] == "RuntimeError"
    assert "iç bağlantı ayrıntısı" not in payload.values()
