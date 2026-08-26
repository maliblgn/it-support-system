from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession, ItOrAdminUser, SettingsDependency
from app.schemas.system import SystemLogPage, SystemOverview
from app.services.system_monitoring import build_system_overview, read_recent_logs

router = APIRouter()
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
OptionalLogLevel = Annotated[LogLevel | None, Query()]
LogLimit = Annotated[int, Query(ge=1, le=200)]


@router.get("/overview", response_model=SystemOverview)
def overview(
    _: ItOrAdminUser,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> SystemOverview:
    return build_system_overview(session, settings)


@router.get("/logs", response_model=SystemLogPage)
def logs(
    _: ItOrAdminUser,
    settings: SettingsDependency,
    level: OptionalLogLevel = None,
    limit: LogLimit = 100,
) -> SystemLogPage:
    return read_recent_logs(settings, level, limit)
