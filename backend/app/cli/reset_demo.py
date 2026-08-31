"""Yerel demo verisini güvenli bir başlangıç durumuna döndürür."""

import argparse
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.cli.seed_demo import _environment_value, sync_demo_accounts
from app.core.config import Settings, get_settings
from app.db.session import dispose_engine, get_session_factory
from app.models.entities import (
    Attachment,
    AuditEvent,
    CannedResponse,
    DeletedAccount,
    Notification,
    Tag,
    Ticket,
    TicketRating,
    TicketTag,
    TicketWatcher,
    User,
)
from app.models.enums import EmailStatus, NotificationType, TicketPriority, UserRole
from app.services.audit import record_audit_event

CONFIRMATION_TEXT = "RESET-DEMO"


@dataclass(frozen=True, slots=True)
class DemoResetResult:
    removed_users: int
    demo_accounts_created: int
    baseline_tickets: int
    removed_upload_entries: int


def _delete_all(session: Session, model: type[object]) -> int:
    result = session.execute(delete(model))
    return result.rowcount or 0


def _seed_baseline(session: Session, users: list[User]) -> int:
    users_by_role = {user.role: user for user in users}
    demo_user = users_by_role[UserRole.USER.value]
    demo_it = users_by_role[UserRole.IT.value]
    demo_admin = users_by_role[UserRole.ADMIN.value]
    now = datetime.now(UTC).replace(tzinfo=None)

    tickets = [
        Ticket(
            ticket_number="IT-000001",
            user_id=demo_user.id,
            subject="Yazıcıdan çıktı alınamıyor",
            description=(
                "Operasyon bölümündeki ağ yazıcısı çevrimdışı görünüyor ve belgeler "
                "yazdırma kuyruğunda bekliyor."
            ),
            department_snapshot=demo_user.department,
            priority=None,
            assigned_to=None,
            is_resolved=False,
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3),
        ),
        Ticket(
            ticket_number="IT-000002",
            user_id=demo_user.id,
            subject="VPN bağlantısı sık sık kopuyor",
            description=(
                "Uzak bağlantı yaklaşık on dakikada bir kesiliyor. Yeniden bağlanınca "
                "çalışmaya devam edilebiliyor."
            ),
            department_snapshot=demo_user.department,
            priority=TicketPriority.HIGH.value,
            assigned_to=demo_it.id,
            is_resolved=False,
            created_at=now - timedelta(hours=8),
            updated_at=now - timedelta(hours=2),
        ),
        Ticket(
            ticket_number="IT-000003",
            user_id=demo_user.id,
            subject="E-posta uygulaması açılmıyor",
            description="Masaüstü e-posta uygulaması açılış ekranında kalıyor.",
            department_snapshot=demo_user.department,
            priority=TicketPriority.NORMAL.value,
            assigned_to=demo_it.id,
            is_resolved=True,
            resolution_outcome="RESOLVED",
            resolution_note=(
                "Bozuk yerel önbellek yeniden oluşturuldu ve e-posta eşitlemesi doğrulandı."
            ),
            resolved_at=now - timedelta(days=1),
            resolved_by=demo_it.id,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        ),
        Ticket(
            ticket_number="IT-000004",
            user_id=demo_user.id,
            subject="Eski rapor ekranına erişilemiyor",
            description="Arşiv raporu açılırken erişim reddedildi uyarısı alınıyor.",
            department_snapshot=demo_user.department,
            priority=TicketPriority.HIGH.value,
            assigned_to=demo_it.id,
            is_resolved=True,
            resolution_outcome="UNRESOLVED",
            resolution_note=(
                "Kaynak sistem erişimi bulunmadığı için inceleme tamamlanamadı; uygulama "
                "yöneticisine yönlendirilmesi gerekiyor."
            ),
            resolved_at=now - timedelta(hours=12),
            resolved_by=demo_it.id,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=12),
        ),
    ]
    session.add_all(tickets)
    session.flush()

    network_tag = Tag(name="Ağ", color="#2563EB", created_by=demo_it.id)
    hardware_tag = Tag(name="Donanım", color="#D97706", created_by=demo_it.id)
    session.add_all([network_tag, hardware_tag])
    session.flush()
    session.add_all(
        [
            TicketTag(ticket_id=tickets[0].id, tag_id=hardware_tag.id, added_by=demo_it.id),
            TicketTag(ticket_id=tickets[1].id, tag_id=network_tag.id, added_by=demo_it.id),
            TicketWatcher(ticket_id=tickets[1].id, user_id=demo_it.id),
            CannedResponse(
                title="Ek bilgi talebi",
                content=(
                    "Sorunu tekrar oluşturduğunuz adımları ve gördüğünüz hata mesajını "
                    "paylaşabilir misiniz?"
                ),
                created_by=demo_admin.id,
            ),
            Notification(
                user_id=demo_it.id,
                ticket_id=tickets[0].id,
                type=NotificationType.NEW_TICKET.value,
                title="Yeni demo talebi",
                message="IT-000001 numaralı talep atama bekliyor.",
                is_read=False,
                email_recipient=demo_it.email,
                email_status=EmailStatus.SKIPPED.value,
                email_attempt_count=0,
            ),
            Notification(
                user_id=demo_user.id,
                ticket_id=tickets[2].id,
                type=NotificationType.TICKET_RESOLVED.value,
                title="Demo talebi çözüldü",
                message="IT-000003 numaralı talep çözüldü olarak sonuçlandırıldı.",
                is_read=False,
                email_recipient=demo_user.email,
                email_status=EmailStatus.SKIPPED.value,
                email_attempt_count=0,
            ),
        ]
    )

    for ticket in tickets:
        record_audit_event(
            session,
            demo_user,
            "TICKET_CREATED",
            "TICKET",
            ticket.id,
            {"ticket_number": ticket.ticket_number, "demo_baseline": True},
        )
        if ticket.assigned_to is not None:
            record_audit_event(
                session,
                demo_admin,
                "TICKET_ASSIGNED_BY_ADMIN",
                "TICKET",
                ticket.id,
                {"assigned_it_user_id": demo_it.id, "demo_baseline": True},
            )
        if ticket.is_resolved:
            record_audit_event(
                session,
                demo_it,
                (
                    "TICKET_RESOLVED"
                    if ticket.resolution_outcome == "RESOLVED"
                    else "TICKET_MARKED_UNRESOLVED"
                ),
                "TICKET",
                ticket.id,
                {"outcome": ticket.resolution_outcome, "demo_baseline": True},
            )
    return len(tickets)


def _clear_upload_root(upload_root: Path) -> int:
    configured_root = upload_root.expanduser()
    if configured_root.is_symlink():
        raise RuntimeError(f"Sembolik bağlantı olan upload kökü temizlenemez: {configured_root}")
    root = configured_root.resolve()
    filesystem_root = Path(root.anchor).resolve()
    forbidden_roots = {filesystem_root, Path.cwd().resolve(), Path.home().resolve()}
    if root in forbidden_roots:
        raise RuntimeError(f"Güvensiz upload kökü temizlenemez: {root}")
    root.mkdir(parents=True, exist_ok=True)

    removed = 0
    for child in root.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            raise RuntimeError(f"Bilinmeyen upload girdisi temizlenemedi: {child}")
        removed += 1
    return removed


def reset_demo_data(settings: Settings | None = None) -> DemoResetResult:
    active_settings = settings or get_settings()
    if not active_settings.demo_mode:
        raise RuntimeError("Demo sıfırlama yalnızca APP_DEMO_MODE=true iken çalıştırılabilir.")
    password = _environment_value("DEMO_ACCOUNT_PASSWORD")

    session = get_session_factory()()
    try:
        _delete_all(session, TicketTag)
        _delete_all(session, TicketWatcher)
        _delete_all(session, TicketRating)
        _delete_all(session, Attachment)
        _delete_all(session, Notification)
        _delete_all(session, AuditEvent)
        _delete_all(session, CannedResponse)
        _delete_all(session, Tag)
        _delete_all(session, Ticket)
        _delete_all(session, DeletedAccount)
        removed_users_result = session.execute(
            delete(User).where(User.email.not_in(active_settings.demo_protected_emails))
        )
        removed_users = removed_users_result.rowcount or 0

        users, created_count = sync_demo_accounts(
            session,
            active_settings,
            password,
            restore_existing=True,
        )
        baseline_tickets = _seed_baseline(session, users)
        if session.bind is not None and session.bind.dialect.name == "mssql":
            session.execute(text("ALTER SEQUENCE dbo.ticket_number_seq RESTART WITH 5"))
        admin_user = next(user for user in users if user.role == UserRole.ADMIN.value)
        record_audit_event(
            session,
            admin_user,
            "DEMO_RESET_COMPLETED",
            "SYSTEM",
            details={"baseline_tickets": baseline_tickets, "removed_users": removed_users},
        )
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()

    removed_upload_entries = _clear_upload_root(active_settings.upload_root_path)
    return DemoResetResult(
        removed_users=removed_users,
        demo_accounts_created=created_count,
        baseline_tickets=baseline_tickets,
        removed_upload_entries=removed_upload_entries,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        required=True,
        choices=[CONFIRMATION_TEXT],
        help=f"Yıkıcı işlemi onaylamak için {CONFIRMATION_TEXT} yazın.",
    )
    parser.parse_args(argv)

    try:
        result = reset_demo_data()
    except Exception as exc:
        print(f"[HATA] Demo sıfırlanamadı: {type(exc).__name__}: {exc}")
        return 1
    finally:
        dispose_engine()

    print(
        "Demo sıfırlama tamamlandı; "
        f"silinen_kullanıcı={result.removed_users}, "
        f"oluşturulan_demo_hesabı={result.demo_accounts_created}, "
        f"örnek_talep={result.baseline_tickets}, "
        f"temizlenen_upload_girdisi={result.removed_upload_entries}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
