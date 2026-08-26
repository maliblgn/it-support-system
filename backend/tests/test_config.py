from urllib.parse import unquote_plus

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_builds_encrypted_trusted_mssql_url() -> None:
    settings = Settings(
        database_url=None,
        database_server="sql01.internal",
        database_name="Tickets",
        database_trusted_connection=True,
        database_encrypt=True,
        database_trust_server_certificate=False,
    )

    uri = settings.sqlalchemy_database_uri
    encoded_connection = uri.partition("odbc_connect=")[2]
    decoded_connection = unquote_plus(encoded_connection)

    assert uri.startswith("mssql+pyodbc:///?odbc_connect=")
    assert "SERVER={sql01.internal,1433}" in decoded_connection
    assert "DATABASE={Tickets}" in decoded_connection
    assert "Trusted_Connection=yes" in decoded_connection
    assert "Encrypt=yes" in decoded_connection
    assert "TrustServerCertificate=no" in decoded_connection


def test_named_mssql_instance_does_not_append_tcp_port() -> None:
    settings = Settings(
        database_url=None,
        database_server=r".\SQLEXPRESS02",
        database_port=1433,
        database_name="Tickets",
        database_trusted_connection=True,
    )

    decoded_connection = unquote_plus(
        settings.sqlalchemy_database_uri.partition("odbc_connect=")[2]
    )

    assert r"SERVER={.\SQLEXPRESS02}" in decoded_connection
    assert r"SQLEXPRESS02,1433" not in decoded_connection


def test_sql_auth_requires_username_and_password() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url=None,
            database_trusted_connection=False,
            database_username=None,
            database_password=None,
        )


def test_sql_auth_password_is_odbc_escaped() -> None:
    settings = Settings(
        database_url=None,
        database_trusted_connection=False,
        database_username="ticket-service",
        database_password="value;with}delimiter",
    )

    encoded_connection = settings.sqlalchemy_database_uri.partition("odbc_connect=")[2]
    decoded_connection = unquote_plus(encoded_connection)

    assert "UID={ticket-service}" in decoded_connection
    assert "PWD={value;with}}delimiter}" in decoded_connection


def test_api_prefix_is_normalized() -> None:
    assert Settings(api_prefix="api/v1/").api_prefix == "/api/v1"


def test_cors_origins_are_normalized_and_deduplicated() -> None:
    assert Settings(
        cors_origins=[" https://support.example.com/ ", "https://support.example.com"]
    ).cors_origins == ["https://support.example.com"]


def test_smtp_requires_sender_address() -> None:
    with pytest.raises(ValidationError):
        Settings(smtp_host="smtp.internal", mail_from=None)


def test_email_delivery_can_be_disabled_without_smtp() -> None:
    settings = Settings(
        **production_settings(
            email_delivery_enabled=False,
            smtp_host=None,
            mail_from=None,
        )
    )

    assert settings.email_delivery_enabled is False


def test_demo_accounts_must_use_an_allowed_domain() -> None:
    with pytest.raises(ValidationError, match="Korunan demo hesapları"):
        Settings(
            allowed_email_domains=["example.com"],
            demo_protected_emails=["demo@invalid.example"],
        )


def test_attachment_size_limit_is_converted_to_bytes() -> None:
    assert Settings(max_attachment_size_mb=10).max_attachment_size_bytes == 10 * 1024 * 1024


def production_settings(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "environment": "production",
        "debug": False,
        "session_secret": "benzersiz-ve-uzun-production-session-secret-2026",
        "session_cookie_secure": True,
        "cors_origins": ["https://support.example.com"],
        "allowed_email_domains": ["example.com"],
        "database_encrypt": True,
        "database_trust_server_certificate": False,
        "database_url": "mssql+pyodbc:///?odbc_connect=production-test",
        "upload_root": "D:/DestekTakip/uploads",
        "smtp_host": "smtp.example.com",
        "mail_from": "tickets@example.com",
    }
    values.update(changes)
    return values


def test_secure_production_settings_are_accepted() -> None:
    settings = Settings(**production_settings())
    assert settings.docs_enabled is False
    assert settings.cookie_secure is True


def test_production_demo_mode_requires_protected_accounts() -> None:
    with pytest.raises(ValidationError, match="demo_protected_emails"):
        Settings(**production_settings(demo_mode=True, demo_protected_emails=[]))


def test_public_production_demo_disables_registration_and_email_delivery() -> None:
    protected = ["demo.user@example.com"]
    settings = Settings(
        **production_settings(
            demo_mode=True,
            demo_protected_emails=protected,
            public_registration_enabled=False,
            email_delivery_enabled=False,
            smtp_host=None,
            mail_from=None,
        )
    )
    assert settings.demo_mode is True

    for field in ("public_registration_enabled", "email_delivery_enabled"):
        changes = {
            "demo_mode": True,
            "demo_protected_emails": protected,
            "public_registration_enabled": False,
            "email_delivery_enabled": False,
            "smtp_host": None,
            "mail_from": None,
        }
        changes[field] = True
        with pytest.raises(ValidationError, match=field):
            Settings(**production_settings(**changes))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("debug", True),
        ("session_cookie_secure", False),
        ("database_encrypt", False),
        ("database_trust_server_certificate", True),
        ("upload_root", "data/uploads"),
        ("smtp_host", None),
        ("cors_origins", ["http://support.example.com"]),
        ("cors_origins", ["https://user:password@support.example.com"]),
        ("cors_origins", ["https://support.example.com/uygulama"]),
        ("database_url", "sqlite+pysqlite:///production.db"),
    ],
)
def test_insecure_production_settings_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match="Production yapılandırması güvenli değil"):
        Settings(**production_settings(**{field: value}))
