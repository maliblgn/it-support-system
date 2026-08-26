from fastapi.testclient import TestClient

from app.main import create_app


def test_liveness_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_with_test_database() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unhandled_error_returns_safe_generic_response() -> None:
    app = create_app()

    @app.get("/test-unhandled")
    def fail() -> None:
        raise RuntimeError("gizli iç ayrıntı")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-unhandled")

    assert response.status_code == 500
    assert response.json() == {"detail": "İşlem sırasında beklenmeyen bir sorun oluştu."}
    assert "gizli" not in response.text
