from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import xlsxwriter
from sqlalchemy import false, func, or_, select, true
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.entities import Ticket, TicketTag, TicketWatcher, User
from app.models.enums import TicketResolutionOutcome
from app.schemas.report import (
    DepartmentTicketCount,
    ItDashboardRead,
    ItPerformanceCount,
    NamedTicketCount,
    ReportPeriod,
    ReportSummary,
    TimeSeriesPoint,
)
from app.schemas.ticket import ItTicketRead

ISTANBUL = ZoneInfo("Europe/Istanbul")
PRIORITY_LABELS = {
    "LOW": "Düşük",
    "NORMAL": "Normal",
    "HIGH": "Yüksek",
    "CRITICAL": "Kritik",
}


class ReportValidationError(ValueError):
    pass


def excel_local_datetime(value: datetime) -> datetime:
    """Convert the database's naive UTC timestamps to naive İstanbul Excel values."""
    return value.replace(tzinfo=UTC).astimezone(ISTANBUL).replace(tzinfo=None)


def priority_label(priority: str | None) -> str:
    return PRIORITY_LABELS.get(priority or "", "Belirlenmedi")


def report_bounds(
    period: ReportPeriod,
    date_from: date | None,
    date_to: date | None,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    local_now = (now or datetime.now(UTC)).astimezone(ISTANBUL)
    if period == ReportPeriod.CUSTOM:
        if date_from is None or date_to is None:
            raise ReportValidationError("Özel tarih aralığında başlangıç ve bitiş zorunludur.")
        if date_from > date_to:
            raise ReportValidationError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        local_start = datetime.combine(date_from, time.min, tzinfo=ISTANBUL)
        local_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=ISTANBUL)
    elif period == ReportPeriod.TODAY:
        local_start = datetime.combine(local_now.date(), time.min, tzinfo=ISTANBUL)
        local_end = local_start + timedelta(days=1)
    elif period == ReportPeriod.WEEK:
        week_start = local_now.date() - timedelta(days=local_now.weekday())
        local_start = datetime.combine(week_start, time.min, tzinfo=ISTANBUL)
        local_end = local_start + timedelta(days=7)
    elif period == ReportPeriod.YEAR:
        year_start = local_now.date().replace(month=1, day=1)
        local_start = datetime.combine(year_start, time.min, tzinfo=ISTANBUL)
        local_end = datetime.combine(
            year_start.replace(year=year_start.year + 1), time.min, tzinfo=ISTANBUL
        )
    else:
        month_start = local_now.date().replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        local_start = datetime.combine(month_start, time.min, tzinfo=ISTANBUL)
        local_end = datetime.combine(next_month, time.min, tzinfo=ISTANBUL)

    return (
        local_start.astimezone(UTC).replace(tzinfo=None),
        local_end.astimezone(UTC).replace(tzinfo=None),
    )


def _filtered_tickets(
    session: Session,
    start_at: datetime,
    end_at: datetime,
) -> list[Ticket]:
    return list(
        session.scalars(
            select(Ticket)
            .options(
                joinedload(Ticket.user),
                joinedload(Ticket.assignee),
                joinedload(Ticket.resolver),
            )
            .where(
                Ticket.created_at >= start_at,
                Ticket.created_at < end_at,
                Ticket.deleted_at.is_(None),
            )
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        ).all()
    )


def build_report_summary(
    session: Session,
    period: ReportPeriod,
    date_from: date | None,
    date_to: date | None,
) -> ReportSummary:
    start_at, end_at = report_bounds(period, date_from, date_to)
    tickets = _filtered_tickets(session, start_at, end_at)
    resolved_tickets = [
        ticket
        for ticket in tickets
        if ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value
    ]
    could_not_resolve = sum(
        ticket.resolution_outcome == TicketResolutionOutcome.UNRESOLVED.value
        for ticket in tickets
    )
    resolution_minutes = [
        (ticket.resolved_at - ticket.created_at).total_seconds() / 60
        for ticket in resolved_tickets
        if ticket.resolved_at is not None
    ]
    department_counts = Counter(ticket.department_snapshot for ticket in tickets)
    priority_counts = Counter(priority_label(ticket.priority) for ticket in tickets)
    it_counts = Counter(ticket.resolved_by for ticket in resolved_tickets if ticket.resolved_by)
    it_names = {
        ticket.resolved_by: f"{ticket.resolver.first_name} {ticket.resolver.last_name}"
        for ticket in resolved_tickets
        if ticket.resolved_by and ticket.resolver is not None
    }
    series_counts = Counter(
        (
            excel_local_datetime(ticket.created_at).strftime("%Y-%m")
            if period == ReportPeriod.YEAR
            else excel_local_datetime(ticket.created_at).strftime("%Y-%m-%d")
        )
        for ticket in tickets
    )
    waiting_minutes = [
        (datetime.now(UTC).replace(tzinfo=None) - ticket.created_at).total_seconds() / 60
        for ticket in tickets
        if not ticket.is_resolved
    ]
    return ReportSummary(
        period=period,
        start_at=start_at.replace(tzinfo=UTC),
        end_at=end_at.replace(tzinfo=UTC),
        total=len(tickets),
        resolved=len(resolved_tickets),
        unresolved=len(tickets) - len(resolved_tickets) - could_not_resolve,
        could_not_resolve=could_not_resolve,
        average_resolution_minutes=(
            round(sum(resolution_minutes) / len(resolution_minutes), 2)
            if resolution_minutes
            else None
        ),
        fastest_resolution_minutes=(
            round(min(resolution_minutes), 2) if resolution_minutes else None
        ),
        longest_waiting_minutes=(round(max(waiting_minutes), 2) if waiting_minutes else None),
        departments=[
            DepartmentTicketCount(department=department, count=count)
            for department, count in sorted(
                department_counts.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ],
        priorities=[
            NamedTicketCount(name=name, count=count)
            for name, count in sorted(priority_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        it_performance=[
            ItPerformanceCount(user_id=user_id, name=it_names[user_id], resolved=count)
            for user_id, count in sorted(
                it_counts.items(), key=lambda item: (-item[1], it_names[item[0]].casefold())
            )
        ],
        time_series=[
            TimeSeriesPoint(label=label, count=count)
            for label, count in sorted(series_counts.items())
        ],
    )


def _dashboard_query():
    return select(Ticket).options(
        joinedload(Ticket.user),
        joinedload(Ticket.assignee),
        selectinload(Ticket.attachments),
        selectinload(Ticket.tag_links).joinedload(TicketTag.tag),
        selectinload(Ticket.watcher_links).joinedload(TicketWatcher.user),
    )


def build_it_dashboard(current_user: User, session: Session) -> ItDashboardRead:
    active = Ticket.deleted_at.is_(None)
    open_ticket = Ticket.is_resolved == false()
    total = session.scalar(select(func.count(Ticket.id)).where(active)) or 0
    open_count = session.scalar(
        select(func.count(Ticket.id)).where(active, open_ticket)
    ) or 0
    resolved = session.scalar(
        select(func.count(Ticket.id)).where(
            active,
            Ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value,
        )
    ) or 0
    could_not_resolve = session.scalar(
        select(func.count(Ticket.id)).where(
            active,
            Ticket.resolution_outcome == TicketResolutionOutcome.UNRESOLVED.value,
        )
    ) or 0
    unassigned = session.scalar(
        select(func.count(Ticket.id)).where(active, open_ticket, Ticket.assigned_to.is_(None))
    ) or 0
    mine = session.scalar(
        select(func.count(Ticket.id)).where(
            active, open_ticket, Ticket.assigned_to == current_user.id
        )
    ) or 0
    high_priority_open = session.scalar(
        select(func.count(Ticket.id)).where(
            active,
            open_ticket,
            or_(Ticket.priority == "HIGH", Ticket.priority == "CRITICAL"),
        )
    ) or 0
    stale_before = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=3)
    stale_open = session.scalar(
        select(func.count(Ticket.id)).where(
            active, open_ticket, Ticket.updated_at < stale_before
        )
    ) or 0
    recent = session.scalars(
        _dashboard_query().where(active).order_by(Ticket.created_at.desc()).limit(5)
    ).all()
    stale = session.scalars(
        _dashboard_query()
        .where(active, open_ticket)
        .order_by(Ticket.updated_at.asc())
        .limit(5)
    ).all()
    recent_resolved = session.scalars(
        _dashboard_query()
        .where(active, Ticket.is_resolved == true())
        .order_by(Ticket.resolved_at.desc())
        .limit(5)
    ).all()
    departments = session.execute(
        select(Ticket.department_snapshot, func.count(Ticket.id))
        .where(active)
        .group_by(Ticket.department_snapshot)
        .order_by(func.count(Ticket.id).desc())
    ).all()
    priorities = session.execute(
        select(Ticket.priority, func.count(Ticket.id))
        .where(active)
        .group_by(Ticket.priority)
        .order_by(func.count(Ticket.id).desc())
    ).all()
    return ItDashboardRead(
        total=total,
        open=open_count,
        resolved=resolved,
        could_not_resolve=could_not_resolve,
        unassigned=unassigned,
        mine=mine,
        high_priority_open=high_priority_open,
        stale_open=stale_open,
        recent=[ItTicketRead.model_validate(ticket) for ticket in recent],
        stale=[ItTicketRead.model_validate(ticket) for ticket in stale],
        recent_resolved=[ItTicketRead.model_validate(ticket) for ticket in recent_resolved],
        departments=[
            DepartmentTicketCount(department=department, count=count)
            for department, count in departments
        ],
        priorities=[
            NamedTicketCount(name=priority_label(priority), count=count)
            for priority, count in priorities
        ],
    )


def build_report_workbook(
    session: Session,
    period: ReportPeriod,
    date_from: date | None,
    date_to: date | None,
) -> bytes:
    start_at, end_at = report_bounds(period, date_from, date_to)
    tickets = _filtered_tickets(session, start_at, end_at)
    resolved_tickets = [
        ticket
        for ticket in tickets
        if ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value
    ]
    could_not_resolve = sum(
        ticket.resolution_outcome == TicketResolutionOutcome.UNRESOLVED.value
        for ticket in tickets
    )
    resolution_minutes_list = [
        (ticket.resolved_at - ticket.created_at).total_seconds() / 60
        for ticket in resolved_tickets
        if ticket.resolved_at is not None
    ]
    average_resolution_minutes = (
        round(sum(resolution_minutes_list) / len(resolution_minutes_list), 2)
        if resolution_minutes_list
        else None
    )
    department_counts = Counter(ticket.department_snapshot for ticket in tickets)
    local_start = excel_local_datetime(start_at)
    local_end = excel_local_datetime(end_at)
    local_range = (
        f"{local_start:%Y-%m-%d %H:%M} — {local_end:%Y-%m-%d %H:%M}"
    )
    output = BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    )
    summary_sheet = workbook.add_worksheet("Özet")
    worksheet = workbook.add_worksheet("Ticket Detayı")
    title_format = workbook.add_format(
        {"bold": True, "font_size": 16, "font_color": "#123B5D"}
    )
    header_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#123B5D",
            "border": 0,
            "text_wrap": True,
        }
    )
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm", "font_color": "#233746"})
    body_format = workbook.add_format({"font_color": "#233746", "valign": "top"})
    resolved_format = workbook.add_format({"font_color": "#237A57", "bold": True})
    open_format = workbook.add_format({"font_color": "#A85B1A", "bold": True})
    metric_value_format = workbook.add_format(
        {
            "bold": True,
            "font_size": 14,
            "font_color": "#123B5D",
            "bg_color": "#EAF2F7",
            "align": "center",
            "valign": "vcenter",
        }
    )

    summary_sheet.hide_gridlines(2)
    summary_sheet.merge_range("A1:F1", "Destek Takip Ticket Raporu", title_format)
    summary_sheet.write("A2", "Tarih aralığı (İstanbul)", body_format)
    summary_sheet.merge_range("B2:F2", local_range, body_format)
    summary_sheet.write_row(3, 0, ["Gösterge", "Değer"], header_format)
    summary_sheet.write_row(4, 0, ["Toplam ticket", len(tickets)], body_format)
    summary_sheet.write_row(5, 0, ["Çözülen", len(resolved_tickets)], body_format)
    summary_sheet.write_row(6, 0, ["Çözülemedi", could_not_resolve], body_format)
    summary_sheet.write_row(
        7,
        0,
        ["Açık", len(tickets) - len(resolved_tickets) - could_not_resolve],
        body_format,
    )
    summary_sheet.write(8, 0, "Ort. çözüm süresi (dk)", body_format)
    if average_resolution_minutes is None:
        summary_sheet.write(8, 1, "—", metric_value_format)
    else:
        summary_sheet.write_number(
            8, 1, average_resolution_minutes, metric_value_format
        )
    summary_sheet.write_row(3, 3, ["Departman", "Ticket sayısı"], header_format)
    for row_index, (department, count) in enumerate(
        sorted(
            department_counts.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        ),
        start=4,
    ):
        summary_sheet.write(row_index, 3, department, body_format)
        summary_sheet.write_number(row_index, 4, count, body_format)
    summary_sheet.set_column("A:A", 28)
    summary_sheet.set_column("B:B", 18)
    summary_sheet.set_column("C:C", 3)
    summary_sheet.set_column("D:D", 26)
    summary_sheet.set_column("E:E", 18)
    summary_sheet.set_column("F:F", 3)
    summary_sheet.set_row(0, 26)
    summary_sheet.set_row(3, 26)

    worksheet.hide_gridlines(2)
    worksheet.merge_range("A1:K1", "Destek Takip Ticket Detayı", title_format)
    worksheet.write("A2", "Tarih aralığı (İstanbul)", body_format)
    worksheet.merge_range("B2:K2", local_range, body_format)
    headers = [
        "Ticket No",
        "Kullanıcı",
        "E-posta",
        "Departman",
        "Konu",
        "Öncelik",
        "Atanan",
        "Oluşturulma",
        "Çözülme",
        "Durum",
        "Çözüm Süresi (dk)",
    ]
    worksheet.write_row(3, 0, headers, header_format)

    for row_index, ticket in enumerate(tickets, start=4):
        assignee_name = (
            f"{ticket.assignee.first_name} {ticket.assignee.last_name}"
            if ticket.assignee is not None
            else "—"
        )
        resolution_minutes = (
            round((ticket.resolved_at - ticket.created_at).total_seconds() / 60, 2)
            if ticket.resolved_at is not None
            else None
        )
        values = [
            ticket.ticket_number,
            f"{ticket.user.first_name} {ticket.user.last_name}",
            ticket.user.email,
            ticket.department_snapshot,
            ticket.subject,
            priority_label(ticket.priority),
            assignee_name,
        ]
        worksheet.write_row(row_index, 0, values, body_format)
        worksheet.write_datetime(
            row_index, 7, excel_local_datetime(ticket.created_at), date_format
        )
        if ticket.resolved_at is not None:
            worksheet.write_datetime(
                row_index, 8, excel_local_datetime(ticket.resolved_at), date_format
            )
        else:
            worksheet.write(row_index, 8, "—", body_format)
        status_text = (
            "Çözüldü"
            if ticket.resolution_outcome == TicketResolutionOutcome.RESOLVED.value
            else "Çözülemedi"
            if ticket.resolution_outcome == TicketResolutionOutcome.UNRESOLVED.value
            else "Açık"
        )
        worksheet.write(
            row_index,
            9,
            status_text,
            resolved_format if status_text == "Çözüldü" else open_format,
        )
        if resolution_minutes is not None:
            worksheet.write_number(row_index, 10, resolution_minutes, body_format)
        else:
            worksheet.write(row_index, 10, "—", body_format)

    worksheet.autofilter(3, 0, max(4, len(tickets) + 3), len(headers) - 1)
    worksheet.freeze_panes(4, 0)
    worksheet.set_column("A:A", 15)
    worksheet.set_column("B:B", 22)
    worksheet.set_column("C:C", 30)
    worksheet.set_column("D:D", 22)
    worksheet.set_column("E:E", 36)
    worksheet.set_column("F:G", 16)
    worksheet.set_column("H:I", 20)
    worksheet.set_column("J:K", 18)
    workbook.close()
    return output.getvalue()
