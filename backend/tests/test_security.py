from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidSessionTokenError,
    create_session_token,
    decode_session_token,
    hash_password,
    validate_allowed_email,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable() -> None:
    settings = Settings()

    first_hash = hash_password("GuvenliParola123", settings)
    second_hash = hash_password("GuvenliParola123", settings)

    assert first_hash != second_hash
    assert verify_password("GuvenliParola123", first_hash)
    assert not verify_password("YanlisParola123", first_hash)


@pytest.mark.parametrize(
    "password",
    ["kisa1", "sadeceharflerden", "123456789012"],
)
def test_password_policy_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(ValueError):
        hash_password(password, Settings())


def test_session_token_round_trip_and_tamper_detection() -> None:
    settings = Settings(session_secret="test-session-secret-at-least-32-chars")
    now = datetime(2026, 8, 21, 10, 0, tzinfo=UTC)
    token = create_session_token(42, settings, now=now)

    claims = decode_session_token(token, settings, now=now + timedelta(minutes=1))

    assert claims.user_id == 42
    assert claims.issued_at == now
    with pytest.raises(InvalidSessionTokenError):
        decode_session_token(f"{token}x", settings, now=now)


def test_expired_session_token_is_rejected() -> None:
    settings = Settings(
        session_secret="test-session-secret-at-least-32-chars",
        session_lifetime_hours=1,
    )
    issued_at = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)
    token = create_session_token(7, settings, now=issued_at)

    with pytest.raises(InvalidSessionTokenError):
        decode_session_token(token, settings, now=issued_at + timedelta(hours=1))


def test_allowed_email_is_normalized_and_restricted() -> None:
    assert validate_allowed_email("  USER@Company.com ", ["company.com"]) == "user@company.com"

    with pytest.raises(ValueError):
        validate_allowed_email("user@example.net", ["company.com"])
