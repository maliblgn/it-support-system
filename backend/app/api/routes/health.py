from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Uygulama sürecinin istek kabul ettiğini doğrular."""
    return HealthResponse()

@router.get("/ready", response_model=HealthResponse)
def readiness() -> HealthResponse:
    """Uygulamanın veritabanına sorgu çalıştırabildiğini doğrular."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Veritabanı bağlantısı hazır değil.",
        ) from exc
    return HealthResponse()
