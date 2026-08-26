import base64
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.core.config import Settings

EMAIL_LOCAL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


class InvalidSessionTokenError(ValueError):
    """Oturum cookie'si doğrulanamadığında kullanılır."""


@dataclass(frozen=True, slots=True)
class SessionClaims:
    user_id: int
    issued_at: datetime
    expires_at: datetime


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if normalized.count("@") != 1:
        raise ValueError("Geçerli bir e-posta adresi girilmelidir.")

    local_part, domain = normalized.rsplit("@", 1)
    if (
        not local_part
        or len(local_part) > 64
        or len(normalized) > 320
        or not EMAIL_LOCAL_PATTERN.fullmatch(local_part)
        or not domain
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or ".." in domain
    ):
        raise ValueError("Geçerli bir e-posta adresi girilmelidir.")
    return normalized


def validate_allowed_email(email: str, allowed_domains: list[str]) -> str:
    normalized = normalize_email(email)
    domain = normalized.rsplit("@", 1)[1]
    if domain not in allowed_domains:
        raise ValueError("Yalnızca izin verilen e-posta alan adları kullanılabilir.")
    return normalized


def account_email_fingerprint(email: str, settings: Settings) -> str:
    normalized = normalize_email(email)
    return hmac.new(
        settings.session_secret.get_secret_value().encode("utf-8"),
        f"deleted-account:{normalized}".encode(),
        hashlib.sha256,
    ).hexdigest()


def validate_password(password: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Şifre {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} karakter arasında olmalıdır."
        )
    if not any(character.isalpha() for character in password):
        raise ValueError("Şifre en az bir harf içermelidir.")
    if not any(character.isdigit() for character in password):
        raise ValueError("Şifre en az bir rakam içermelidir.")


def hash_password(password: str, settings: Settings) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=settings.password_scrypt_n,
        r=settings.password_scrypt_r,
        p=settings.password_scrypt_p,
        dklen=32,
        maxmem=128 * 1024 * 1024,
    )
    return "$".join(
        [
            "scrypt",
            str(settings.password_scrypt_n),
            str(settings.password_scrypt_r),
            str(settings.password_scrypt_p),
            _b64_encode(salt),
            _b64_encode(derived_key),
        ]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, n_text, r_text, p_text, salt_text, expected_text = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        n = int(n_text)
        r = int(r_text)
        p = int(p_text)
        if n < 16384 or n > 1048576 or n & (n - 1) or not 1 <= r <= 32 or not 1 <= p <= 16:
            return False
        salt = _b64_decode(salt_text)
        expected = _b64_decode(expected_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
            maxmem=128 * 1024 * 1024,
        )
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(actual, expected)


@lru_cache(maxsize=8)
def dummy_password_hash(n: int, r: int, p: int) -> str:
    settings = Settings(password_scrypt_n=n, password_scrypt_r=r, password_scrypt_p=p)
    return hash_password("Timing-Only-Password-123", settings)


def create_session_token(user_id: int, settings: Settings, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(hours=settings.session_lifetime_hours)
    payload = {
        "exp": int(expires_at.timestamp()),
        "iat": int(issued_at.timestamp()),
        "sub": user_id,
        "v": 1,
    }
    encoded_payload = _b64_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.session_secret.get_secret_value().encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_b64_encode(signature)}"


def decode_session_token(
    token: str, settings: Settings, now: datetime | None = None
) -> SessionClaims:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        supplied_signature = _b64_decode(encoded_signature)
        expected_signature = hmac.new(
            settings.session_secret.get_secret_value().encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise InvalidSessionTokenError("Geçersiz imza.")

        payload = json.loads(_b64_decode(encoded_payload))
        if payload.get("v") != 1:
            raise InvalidSessionTokenError("Desteklenmeyen oturum sürümü.")
        user_id = int(payload["sub"])
        issued_at = datetime.fromtimestamp(int(payload["iat"]), tz=UTC)
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, InvalidSessionTokenError):
            raise
        raise InvalidSessionTokenError("Oturum verisi okunamadı.") from exc

    current_time = now or datetime.now(UTC)
    if (
        user_id <= 0
        or issued_at > current_time + timedelta(minutes=1)
        or expires_at <= current_time
    ):
        raise InvalidSessionTokenError("Oturum süresi veya kullanıcı kimliği geçersiz.")
    return SessionClaims(user_id=user_id, issued_at=issued_at, expires_at=expires_at)


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)
