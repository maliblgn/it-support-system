import hashlib
import logging
import os
import unicodedata
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import Attachment, Ticket, User
from app.models.enums import UserRole
from app.services.audit import record_audit_event
from app.services.notifications import notify_ticket_watchers

logger = logging.getLogger(__name__)
CHUNK_SIZE = 64 * 1024
SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "application/pdf": (b"%PDF-",),
}
EXTENSIONS_BY_TYPE = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "application/pdf": {".pdf"},
}


class AttachmentNotFoundError(LookupError):
    pass


class AttachmentValidationError(ValueError):
    pass


class AttachmentConflictError(RuntimeError):
    pass


def _normalize_original_name(filename: str | None) -> tuple[str, str]:
    if filename is None:
        raise AttachmentValidationError("Dosya adı zorunludur.")
    normalized = unicodedata.normalize("NFC", filename).strip()
    if (
        not normalized
        or len(normalized) > 255
        or normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or "\x00" in normalized
    ):
        raise AttachmentValidationError("Dosya adı güvenli değil.")
    extension = Path(normalized).suffix.casefold()
    return normalized, extension


def _validate_signature(content_type: str, extension: str, header: bytes) -> None:
    allowed_extensions = EXTENSIONS_BY_TYPE.get(content_type)
    signatures = SIGNATURES.get(content_type)
    if allowed_extensions is None or signatures is None:
        raise AttachmentValidationError("Yalnızca PNG, JPG/JPEG ve PDF dosyaları kabul edilir.")
    if extension not in allowed_extensions:
        raise AttachmentValidationError("Dosya uzantısı ile MIME türü eşleşmiyor.")
    if not any(header.startswith(signature) for signature in signatures):
        raise AttachmentValidationError("Dosya içeriği bildirilen türle eşleşmiyor.")


def _storage_path(storage_key: str, settings: Settings) -> Path:
    root = settings.upload_root_path
    relative_parts = PurePosixPath(storage_key).parts
    if not relative_parts or any(part in {"", ".", ".."} for part in relative_parts):
        raise AttachmentValidationError("Geçersiz depolama anahtarı.")
    candidate = root.joinpath(*relative_parts).resolve()
    if not candidate.is_relative_to(root):
        raise AttachmentValidationError("Geçersiz depolama yolu.")
    return candidate


def get_authorized_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: User,
    session: Session,
) -> Attachment:
    query = (
        select(Attachment)
        .join(Attachment.ticket)
        .where(Attachment.id == attachment_id, Attachment.ticket_id == ticket_id)
    )
    query = query.where(Ticket.deleted_at.is_(None))
    if current_user.role not in {UserRole.IT.value, UserRole.ADMIN.value}:
        query = query.where(Ticket.user_id == current_user.id)
    attachment = session.scalar(query)
    if attachment is None:
        raise AttachmentNotFoundError("Dosya eki bulunamadı.")
    return attachment


async def store_attachment(
    ticket: Ticket,
    current_user: User,
    upload: UploadFile,
    session: Session,
    settings: Settings,
) -> Attachment:
    if ticket.is_resolved:
        raise AttachmentConflictError("Çözülmüş ticket'a dosya eklenemez.")
    attachment_count = session.scalar(
        select(func.count(Attachment.id)).where(Attachment.ticket_id == ticket.id)
    )
    if (attachment_count or 0) >= settings.max_attachments_per_ticket:
        raise AttachmentConflictError("Ticket için dosya eki sınırına ulaşıldı.")

    original_name, extension = _normalize_original_name(upload.filename)
    content_type = (upload.content_type or "").split(";", 1)[0].strip().casefold()
    stored_name = str(uuid4())
    storage_key = PurePosixPath(str(ticket.id), stored_name).as_posix()
    final_path = _storage_path(storage_key, settings)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = final_path.with_name(f".{stored_name}.{uuid4().hex}.uploading")
    digest = hashlib.sha256()
    size = 0
    header = b""

    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_attachment_size_bytes:
                    raise AttachmentValidationError(
                        f"Dosya boyutu {settings.max_attachment_size_mb} MB sınırını aşıyor."
                    )
                if len(header) < 16:
                    header = (header + chunk)[:16]
                digest.update(chunk)
                destination.write(chunk)
        if size == 0:
            raise AttachmentValidationError("Boş dosya yüklenemez.")
        _validate_signature(content_type, extension, header)
        os.replace(temporary_path, final_path)

        attachment = Attachment(
            ticket_id=ticket.id,
            uploaded_by=current_user.id,
            original_file_name=original_name,
            stored_file_name=stored_name,
            storage_key=storage_key,
            content_type=content_type,
            file_extension=extension,
            file_size_bytes=size,
            sha256=digest.hexdigest(),
        )
        session.add(attachment)
        session.flush()
        record_audit_event(
            session,
            current_user,
            "TICKET_ATTACHMENT_ADDED",
            "TICKET",
            ticket.id,
            {
                "attachment_id": attachment.id,
                "file_name": attachment.original_file_name,
                "file_size_bytes": size,
            },
        )
        session.commit()
    except (AttachmentValidationError, SQLAlchemyError):
        session.rollback()
        temporary_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    logger.info(
        "Ticket dosya eki yüklendi.",
        extra={
            "attachment_id": attachment.id,
            "ticket_id": ticket.id,
            "user_id": current_user.id,
            "file_size_bytes": size,
        },
    )
    notify_ticket_watchers(
        ticket,
        current_user,
        f"Dosya eklendi: {ticket.ticket_number}",
        f"{ticket.ticket_number} numaralı ticket'a {attachment.original_file_name} eklendi.",
        session,
        settings,
    )
    return attachment


def attachment_file_path(attachment: Attachment, settings: Settings) -> Path:
    path = _storage_path(attachment.storage_key, settings)
    if not path.is_file():
        logger.error(
            "Dosya eki metadata'sı var ancak dosya diskte bulunamadı.",
            extra={"attachment_id": attachment.id, "ticket_id": attachment.ticket_id},
        )
        raise AttachmentNotFoundError("Dosya eki bulunamadı.")
    return path


def delete_own_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: User,
    session: Session,
    settings: Settings,
) -> None:
    attachment = session.scalar(
        select(Attachment)
        .join(Attachment.ticket)
        .where(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id,
            Ticket.user_id == current_user.id,
            Attachment.uploaded_by == current_user.id,
            Ticket.deleted_at.is_(None),
        )
    )
    if attachment is None:
        raise AttachmentNotFoundError("Dosya eki bulunamadı.")
    if attachment.ticket.is_resolved:
        raise AttachmentConflictError("Çözülmüş ticket'ın dosya eki kaldırılamaz.")

    path = _storage_path(attachment.storage_key, settings)
    quarantine = path.with_name(f".{path.name}.{uuid4().hex}.deleting")
    if path.exists():
        os.replace(path, quarantine)
    try:
        record_audit_event(
            session,
            current_user,
            "TICKET_ATTACHMENT_REMOVED",
            "TICKET",
            ticket_id,
            {"attachment_id": attachment_id, "file_name": attachment.original_file_name},
        )
        session.delete(attachment)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        if quarantine.exists():
            os.replace(quarantine, path)
        raise
    quarantine.unlink(missing_ok=True)
    logger.info(
        "Ticket dosya eki kaldırıldı.",
        extra={
            "attachment_id": attachment_id,
            "ticket_id": ticket_id,
            "user_id": current_user.id,
        },
    )
    notify_ticket_watchers(
        attachment.ticket,
        current_user,
        f"Dosya kaldırıldı: {attachment.ticket.ticket_number}",
        f"{attachment.original_file_name} adlı dosya ticket üzerinden kaldırıldı.",
        session,
        settings,
    )
