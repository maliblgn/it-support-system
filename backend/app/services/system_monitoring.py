import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.system import SystemLogEntry, SystemLogPage, SystemOverview

PROCESS_STARTED_AT = monotonic()


def _database_status(session: Session) -> str:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return "error"
    return "ok"


def _upload_status(path: Path) -> tuple[str, int | None]:
    try:
        if not path.is_dir() or not os.access(path, os.R_OK | os.W_OK):
            return "error", None
        return "ok", shutil.disk_usage(path).free
    except OSError:
        return "error", None


def build_system_overview(session: Session, settings: Settings) -> SystemOverview:
    database_status = _database_status(session)
    upload_status, upload_free_bytes = _upload_status(settings.upload_root_path)
    log_file = settings.log_file_path
    try:
        log_size = log_file.stat().st_size if log_file and log_file.is_file() else 0
    except OSError:
        log_size = 0
    return SystemOverview(
        status="ok" if database_status == upload_status == "ok" else "degraded",
        app_version=settings.app_version,
        environment=settings.environment,
        database_status=database_status,
        upload_status=upload_status,
        upload_free_bytes=upload_free_bytes,
        log_file_enabled=log_file is not None,
        log_size_bytes=log_size,
        uptime_seconds=max(0, int(monotonic() - PROCESS_STARTED_AT)),
        checked_at=datetime.now(UTC),
    )


def _candidate_log_files(log_file: Path) -> list[Path]:
    backups = sorted(
        log_file.parent.glob(f"{log_file.name}.*"),
        key=lambda path: path.stat().st_mtime,
    )
    return [*backups, log_file]


def read_recent_logs(
    settings: Settings,
    level: str | None,
    limit: int,
) -> SystemLogPage:
    log_file = settings.log_file_path
    if log_file is None:
        return SystemLogPage(items=[], returned=0)

    entries: list[SystemLogEntry] = []
    normalized_level = level.upper() if level else None
    for path in _candidate_log_files(log_file):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                payload = json.loads(line)
                entry = SystemLogEntry.model_validate(payload)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            if normalized_level and entry.level != normalized_level:
                continue
            entries.append(entry)

    entries.sort(key=lambda entry: entry.timestamp, reverse=True)
    selected = entries[:limit]
    return SystemLogPage(items=selected, returned=len(selected))
