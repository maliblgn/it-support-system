import json
import logging
import logging.config
from datetime import UTC, datetime
from pathlib import Path

SAFE_CONTEXT_FIELDS = (
    "user_id",
    "it_user_id",
    "ticket_id",
    "ticket_number",
    "attachment_id",
    "notification_id",
    "role",
    "priority",
    "file_size_bytes",
    "unmatched_recipient_count",
    "http_method",
    "request_path",
    "status_code",
)


class SafeContextFormatter(logging.Formatter):
    """Yalnızca onaylı operasyon alanlarını log satırına ekler."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        context = " ".join(
            f"{field}={getattr(record, field)}"
            for field in SAFE_CONTEXT_FIELDS
            if hasattr(record, field)
        )
        return f"{message} {context}" if context else message


class JsonContextFormatter(logging.Formatter):
    """Merkezi izleme için güvenli, satır bazlı JSON log üretir."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = {
            field: getattr(record, field)
            for field in SAFE_CONTEXT_FIELDS
            if hasattr(record, field)
        }
        if context:
            payload["context"] = context
        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def configure_logging(
    level: str,
    log_file: Path | None = None,
    log_max_bytes: int = 10 * 1024 * 1024,
    log_backup_count: int = 5,
) -> None:
    handlers: dict[str, dict[str, object]] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": level,
        }
    }
    root_handlers = ["console"]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers["json_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "level": level,
            "filename": str(log_file),
            "maxBytes": log_max_bytes,
            "backupCount": log_backup_count,
            "encoding": "utf-8",
            "delay": True,
        }
        root_handlers.append("json_file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": SafeContextFormatter,
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
                "json": {"()": JsonContextFormatter},
            },
            "handlers": handlers,
            "root": {"handlers": root_handlers, "level": level},
            "loggers": {
                "sqlalchemy.engine": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": root_handlers,
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )
