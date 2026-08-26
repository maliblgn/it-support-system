from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.schemas.ticket import ItTicketRead


class ReportPeriod(StrEnum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


class DepartmentTicketCount(BaseModel):
    department: str
    count: int


class NamedTicketCount(BaseModel):
    name: str
    count: int


class ItPerformanceCount(BaseModel):
    user_id: int
    name: str
    resolved: int


class TimeSeriesPoint(BaseModel):
    label: str
    count: int


class ReportSummary(BaseModel):
    period: ReportPeriod
    start_at: datetime
    end_at: datetime
    total: int
    resolved: int
    unresolved: int
    could_not_resolve: int
    average_resolution_minutes: float | None
    fastest_resolution_minutes: float | None
    longest_waiting_minutes: float | None
    departments: list[DepartmentTicketCount]
    priorities: list[NamedTicketCount]
    it_performance: list[ItPerformanceCount]
    time_series: list[TimeSeriesPoint]


class ItDashboardRead(BaseModel):
    total: int
    open: int
    resolved: int
    could_not_resolve: int
    unassigned: int
    mine: int
    high_priority_open: int
    stale_open: int
    recent: list[ItTicketRead]
    stale: list[ItTicketRead]
    recent_resolved: list[ItTicketRead]
    departments: list[DepartmentTicketCount]
    priorities: list[NamedTicketCount]
