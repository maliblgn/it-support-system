from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import authorize_resource_owner, require_it_user
from app.core.config import get_settings
from app.core.security import account_email_fingerprint
from app.db.session import get_session_factory
from app.main import create_app
from app.models.entities import DeletedAccount, User
from app.models.enums import UserRole
from app.services.auth import _is_email_unique_violation


def registration_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "ayse.yilmaz@company.com",
        "password": "GuvenliParola123",
        "first_name": "Ayşe",
        "last_name": "Yılmaz",
        "phone": "+90 555 000 00 00",
        "department": "Finans",
    }
    payload.update(changes)
    return payload


def test_registration_creates_only_user_role_and_sets_secure_session_cookies() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/auth/register",
            json=registration_payload(email="  AYSE.YILMAZ@company.com  "),
        )

    assert response.status_code == 201
    assert response.json()["email"] == "ayse.yilmaz@company.com"
    assert response.json()["role"] == UserRole.USER.value
    assert client.cookies.get("it_ticket_session")
    assert client.cookies.get("it_ticket_csrf")
    assert "HttpOnly" in response.headers.get_list("set-cookie")[0]


def test_registration_forbids_role_injection_and_external_domains() -> None:
    with TestClient(create_app()) as client:
        role_response = client.post(
            "/api/auth/register",
            json=registration_payload(role=UserRole.IT.value),
        )
        domain_response = client.post(
            "/api/auth/register",
            json=registration_payload(email="ayse@example.net"),
        )

    assert role_response.status_code == 422
    assert domain_response.status_code == 422


def test_public_registration_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("APP_PUBLIC_REGISTRATION_ENABLED", "false")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post("/api/auth/register", json=registration_payload())

    assert response.status_code == 403
    assert "Demo" in response.json()["detail"]


def test_demo_account_cannot_change_shared_profile_or_password(monkeypatch) -> None:
    protected_email = "demo.user@company.com"
    monkeypatch.setenv("APP_DEMO_MODE", "true")
    monkeypatch.setenv("APP_DEMO_PROTECTED_EMAILS", f'["{protected_email}"]')
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        created = client.post(
            "/api/auth/register",
            json=registration_payload(email=protected_email),
        )
        profile_update = client.patch(
            "/api/users/me",
            json={"first_name": "Değiştirilemez"},
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )
        password_update = client.post(
            "/api/users/me/password",
            json={
                "current_password": "GuvenliParola123",
                "new_password": "YeniGuvenliParola123",
            },
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )

    assert created.status_code == 201
    assert profile_update.status_code == 409
    assert password_update.status_code == 409
    assert "demo hesab" in profile_update.json()["detail"]


def test_duplicate_registration_returns_conflict() -> None:
    with TestClient(create_app()) as client:
        first_response = client.post("/api/auth/register", json=registration_payload())
        csrf_token = client.cookies["it_ticket_csrf"]
        second_response = client.post(
            "/api/auth/register",
            json=registration_payload(),
            headers={"X-CSRF-Token": csrf_token},
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_me_and_logout_flow_enforces_csrf() -> None:
    with patch("app.api.routes.auth.logger") as auth_logger:
        with TestClient(create_app()) as client:
            assert client.get("/api/auth/me").status_code == 401
            assert client.post("/api/auth/register", json=registration_payload()).status_code == 201

            client.cookies.clear()
            wrong_login = client.post(
                "/api/auth/login",
                json={"email": "ayse.yilmaz@company.com", "password": "YanlisParola123"},
            )
            login = client.post(
                "/api/auth/login",
                json={"email": "ayse.yilmaz@company.com", "password": "GuvenliParola123"},
            )
            me = client.get("/api/auth/me")
            logout_without_csrf = client.post("/api/auth/logout")
            csrf_token = client.cookies["it_ticket_csrf"]
            logout = client.post(
                "/api/auth/logout",
                headers={"X-CSRF-Token": csrf_token},
            )

    assert wrong_login.status_code == 401
    assert login.status_code == 200
    assert me.status_code == 200
    assert logout_without_csrf.status_code == 403
    assert logout.status_code == 204
    assert client.cookies.get("it_ticket_session") is None
    auth_logger.warning.assert_called_once_with("Başarısız giriş denemesi.")
    assert auth_logger.info.call_count == 3


def test_profile_update_requires_csrf_and_persists_changes() -> None:
    with TestClient(create_app()) as client:
        assert client.post("/api/auth/register", json=registration_payload()).status_code == 201

        denied = client.patch("/api/users/me", json={"department": "Satın Alma"})
        updated = client.patch(
            "/api/users/me",
            json={
                "email": "ayse.yeni@company.com",
                "department": "Satın Alma",
                "phone": None,
            },
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )
        invalid_email = client.patch(
            "/api/users/me",
            json={"email": "ayse@example.net"},
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )
        invalid_department = client.patch(
            "/api/users/me",
            json={"department": None},
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )
        profile = client.get("/api/users/me")

    assert denied.status_code == 403
    assert updated.status_code == 200
    assert invalid_email.status_code == 422
    assert invalid_department.status_code == 422
    assert updated.json()["email"] == "ayse.yeni@company.com"
    assert updated.json()["department"] == "Satın Alma"
    assert profile.json()["department"] == "Satın Alma"
    assert profile.json()["phone"] is None


def test_profile_email_must_remain_unique() -> None:
    with TestClient(create_app()) as client:
        assert client.post("/api/auth/register", json=registration_payload()).status_code == 201
        client.cookies.clear()
        assert client.post(
            "/api/auth/register",
            json=registration_payload(email="mehmet@company.com", first_name="Mehmet"),
        ).status_code == 201

        duplicate = client.patch(
            "/api/users/me",
            json={"email": "ayse.yilmaz@company.com"},
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Bu e-posta adresi zaten kayıtlı."


def test_profile_email_cannot_reuse_a_permanently_deleted_address() -> None:
    settings = get_settings()
    deleted_email = "silinmis@company.com"
    with TestClient(create_app()) as client:
        assert client.post("/api/auth/register", json=registration_payload()).status_code == 201
        with get_session_factory()() as session:
            session.add(
                DeletedAccount(
                    email_hash=account_email_fingerprint(deleted_email, settings)
                )
            )
            session.commit()

        blocked = client.patch(
            "/api/users/me",
            json={"email": deleted_email},
            headers={"X-CSRF-Token": client.cookies["it_ticket_csrf"]},
        )

    assert blocked.status_code == 409
    assert "kalıcı olarak silinmiştir" in blocked.json()["detail"]


def test_role_and_owner_authorization_do_not_reveal_foreign_resources() -> None:
    regular_user = User(id=10, role=UserRole.USER.value)
    it_user = User(id=20, role=UserRole.IT.value)

    authorize_resource_owner(regular_user, owner_user_id=10)
    authorize_resource_owner(it_user, owner_user_id=10)

    with pytest.raises(HTTPException) as hidden_resource:
        authorize_resource_owner(regular_user, owner_user_id=99)
    with pytest.raises(HTTPException) as forbidden_role:
        require_it_user(regular_user)

    assert hidden_resource.value.status_code == 404
    assert forbidden_role.value.status_code == 403
    assert require_it_user(it_user) is it_user


def test_only_email_unique_integrity_error_is_classified_as_duplicate() -> None:
    duplicate = IntegrityError("INSERT", {}, Exception("UQ_users_email duplicate key"))
    unrelated = IntegrityError("INSERT", {}, Exception("Cannot insert timestamp value"))

    assert _is_email_unique_violation(duplicate) is True
    assert _is_email_unique_violation(unrelated) is False
