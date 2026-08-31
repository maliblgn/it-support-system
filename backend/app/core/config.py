from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus, urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Destek Takip API"
    app_version: str = "0.7.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_file: Path | None = None
    log_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024 * 1024, le=1024 * 1024 * 1024)
    log_backup_count: int = Field(default=5, ge=1, le=100)
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    allowed_email_domains: list[str] = Field(default_factory=lambda: ["example.com"])
    public_registration_enabled: bool = True
    demo_mode: bool = False
    demo_protected_emails: list[str] = Field(default_factory=list)

    session_secret: SecretStr = SecretStr(
        "development-only-change-this-session-secret"
    )
    session_lifetime_hours: int = Field(default=8, ge=1, le=24)
    session_cookie_name: str = "it_ticket_session"
    csrf_cookie_name: str = "it_ticket_csrf"
    session_cookie_secure: bool | None = None
    password_scrypt_n: int = Field(default=16384, ge=16384, le=1048576)
    password_scrypt_r: int = Field(default=8, ge=1, le=32)
    password_scrypt_p: int = Field(default=1, ge=1, le=16)

    upload_root: Path = Path("data/uploads")
    max_attachment_size_mb: int = Field(default=10, ge=1, le=100)
    max_attachments_per_ticket: int = Field(default=5, ge=1, le=20)

    email_delivery_enabled: bool = True
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=60)
    mail_from: str | None = None
    it_notification_recipients: list[str] = Field(default_factory=list)

    database_url: str | None = None
    database_server: str = "localhost"
    database_port: int = Field(default=1433, ge=1, le=65535)
    database_name: str = "DestekTakip"
    database_driver: str = "ODBC Driver 18 for SQL Server"
    database_trusted_connection: bool = True
    database_username: str | None = None
    database_password: SecretStr | None = None
    database_encrypt: bool = True
    database_trust_server_certificate: bool = False
    database_connection_timeout_seconds: int = Field(default=5, ge=1, le=60)
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level şu değerlerden biri olmalıdır: {sorted(allowed)}")
        return normalized

    @field_validator("log_file", mode="before")
    @classmethod
    def normalize_log_file(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @field_validator("allowed_email_domains")
    @classmethod
    def normalize_email_domains(cls, values: list[str]) -> list[str]:
        normalized = sorted(
            {value.strip().casefold().lstrip("@") for value in values if value.strip()}
        )
        if not normalized:
            raise ValueError("En az bir izin verilen e-posta alan adı tanımlanmalıdır.")
        return normalized

    @field_validator("demo_protected_emails")
    @classmethod
    def normalize_demo_protected_emails(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().casefold() for value in values if value.strip()})
        if any(
            value.count("@") != 1
            or not value.rsplit("@", 1)[0]
            or "." not in value.rsplit("@", 1)[1]
            or value.rsplit("@", 1)[1].startswith(".")
            or value.rsplit("@", 1)[1].endswith(".")
            for value in normalized
        ):
            raise ValueError("Korunan demo hesapları geçerli e-posta adresleri olmalıdır.")
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def normalize_cors_origins(cls, values: list[str]) -> list[str]:
        return sorted({value.strip().rstrip("/") for value in values if value.strip()})

    @field_validator("password_scrypt_n")
    @classmethod
    def validate_scrypt_n(cls, value: int) -> int:
        if value & (value - 1):
            raise ValueError("password_scrypt_n ikinin kuvveti olmalıdır.")
        return value

    @field_validator("smtp_host", "smtp_username", "mail_from")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("it_notification_recipients")
    @classmethod
    def normalize_notification_recipients(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().casefold() for value in values if value.strip()})
        if any(value.count("@") != 1 for value in normalized):
            raise ValueError("IT bildirim alıcıları geçerli e-posta adresleri olmalıdır.")
        return normalized

    @model_validator(mode="after")
    def validate_database_credentials(self) -> "Settings":
        if self.environment.casefold() == "production":
            secret = self.session_secret.get_secret_value()
            insecure: list[str] = []
            if secret.startswith("development-only-") or len(secret) < 32:
                insecure.append("en az 32 karakterlik benzersiz session_secret")
            if self.debug:
                insecure.append("debug=false")
            if self.session_cookie_secure is False:
                insecure.append("session_cookie_secure=true")
            if not self.database_encrypt:
                insecure.append("database_encrypt=true")
            if self.database_trust_server_certificate:
                insecure.append("database_trust_server_certificate=false")
            if self.database_url and not self.database_url.casefold().startswith("mssql+pyodbc:"):
                insecure.append("mssql+pyodbc production veritabanı")
            if not self.upload_root.is_absolute():
                insecure.append("mutlak bir upload_root yolu")
            if self.email_delivery_enabled and not self.smtp_host:
                insecure.append("SMTP host ve gönderici ayarları")
            if self.demo_mode and not self.demo_protected_emails:
                insecure.append("demo_mode için en az bir demo_protected_emails hesabı")
            if self.demo_mode and self.public_registration_enabled:
                insecure.append("demo_mode için public_registration_enabled=false")
            if self.demo_mode and self.email_delivery_enabled:
                insecure.append("demo_mode için email_delivery_enabled=false")
            if not self.cors_origins or any(
                (parts := urlsplit(origin)).scheme.casefold() != "https"
                or not parts.netloc
                or bool(parts.path or parts.query or parts.fragment)
                or "@" in parts.netloc
                for origin in self.cors_origins
            ):
                insecure.append("yalnızca HTTPS içeren cors_origins")
            if insecure:
                raise ValueError(
                    "Production yapılandırması güvenli değil; gerekli: " + ", ".join(insecure)
                )
        invalid_demo_domains = [
            email
            for email in self.demo_protected_emails
            if email.rsplit("@", 1)[1] not in self.allowed_email_domains
        ]
        if invalid_demo_domains:
            raise ValueError(
                "Korunan demo hesapları izin verilen e-posta alan adlarından birini kullanmalıdır."
            )
        if self.smtp_host and not self.mail_from:
            raise ValueError("SMTP etkinse mail_from zorunludur.")
        if self.smtp_username and self.smtp_password is None:
            raise ValueError("SMTP kullanıcı adı tanımlıysa smtp_password zorunludur.")
        if self.database_url or self.database_trusted_connection:
            return self
        password = (
            self.database_password.get_secret_value() if self.database_password is not None else ""
        )
        if not (self.database_username or "").strip() or not password:
            raise ValueError(
                "SQL authentication için database_username ve database_password zorunludur."
            )
        return self

    @staticmethod
    def _odbc_braced(value: str) -> str:
        """ODBC değerlerini noktalı virgül ve kapanış süslü paranteze karşı güvenli yapar."""
        return "{" + value.replace("}", "}}") + "}"

    @property
    def docs_enabled(self) -> bool:
        return self.environment.casefold() != "production" or self.debug

    @property
    def cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.environment.casefold() == "production"

    @property
    def upload_root_path(self) -> Path:
        return self.upload_root.expanduser().resolve()

    @property
    def log_file_path(self) -> Path | None:
        return self.log_file.expanduser().resolve() if self.log_file is not None else None

    @property
    def max_attachment_size_bytes(self) -> int:
        return self.max_attachment_size_mb * 1024 * 1024

    def is_demo_account_protected(self, email: str) -> bool:
        return self.demo_mode and email.strip().casefold() in self.demo_protected_emails

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url

        server_target = self.database_server
        # Named instance (örn. .\SQLEXPRESS) bağlantılarında TCP portu instance tarafından
        # çözülür; normal host adlarında yapılandırılmış port açıkça eklenir.
        if "\\" not in server_target:
            server_target = f"{server_target},{self.database_port}"

        connection_parts = [
            f"DRIVER={self._odbc_braced(self.database_driver)}",
            f"SERVER={self._odbc_braced(server_target)}",
            f"DATABASE={self._odbc_braced(self.database_name)}",
        ]

        if self.database_trusted_connection:
            connection_parts.append("Trusted_Connection=yes")
        else:
            connection_parts.extend(
                [
                    f"UID={self._odbc_braced(self.database_username)}",
                    f"PWD={self._odbc_braced(self.database_password.get_secret_value())}",
                ]
            )

        connection_parts.extend(
            [
                f"Encrypt={'yes' if self.database_encrypt else 'no'}",
                "TrustServerCertificate="
                f"{'yes' if self.database_trust_server_certificate else 'no'}",
                f"Connection Timeout={self.database_connection_timeout_seconds}",
            ]
        )
        odbc_connect = ";".join(connection_parts)
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_connect)}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
