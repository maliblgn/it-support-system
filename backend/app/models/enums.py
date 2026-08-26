from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    IT = "IT"
    ADMIN = "ADMIN"


class TicketPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketResolutionOutcome(StrEnum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class NotificationType(StrEnum):
    NEW_TICKET = "NEW_TICKET"
    TICKET_UPDATED = "TICKET_UPDATED"
    TICKET_RESOLVED = "TICKET_RESOLVED"
    TICKET_UNRESOLVED = "TICKET_UNRESOLVED"
    TICKET_DELETED = "TICKET_DELETED"
    TICKET_RATED = "TICKET_RATED"


class EmailStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
