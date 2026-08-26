from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.dependencies import DatabaseSession, ItOrAdminUser, ItUser
from app.schemas.report import ItDashboardRead, ReportPeriod, ReportSummary
from app.services.reports import (
    ReportValidationError,
    build_it_dashboard,
    build_report_summary,
    build_report_workbook,
)

router = APIRouter()
OptionalDate = Annotated[date | None, Query()]


@router.get("/dashboard", response_model=ItDashboardRead)
def dashboard(current_user: ItUser, session: DatabaseSession) -> ItDashboardRead:
    return build_it_dashboard(current_user, session)


def _validation_error(exc: ReportValidationError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=str(exc),
    )


@router.get("/summary", response_model=ReportSummary)
def summary(
    _: ItOrAdminUser,
    session: DatabaseSession,
    period: ReportPeriod = ReportPeriod.MONTH,
    date_from: OptionalDate = None,
    date_to: OptionalDate = None,
) -> ReportSummary:
    try:
        return build_report_summary(session, period, date_from, date_to)
    except ReportValidationError as exc:
        raise _validation_error(exc) from exc


@router.get("/export.xlsx")
def export_excel(
    _: ItOrAdminUser,
    session: DatabaseSession,
    period: ReportPeriod = ReportPeriod.MONTH,
    date_from: OptionalDate = None,
    date_to: OptionalDate = None,
) -> Response:
    try:
        content = build_report_workbook(session, period, date_from, date_to)
    except ReportValidationError as exc:
        raise _validation_error(exc) from exc
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="ticket-report-{timestamp}.xlsx"'
        },
    )
