import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import CsrfOriginMiddleware
from app.db.session import dispose_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(
        settings.log_level,
        settings.log_file_path,
        settings.log_max_bytes,
        settings.log_backup_count,
    )
    logger.info("Uygulama başlatıldı.")
    try:
        yield
    finally:
        logger.info("Uygulama durduruluyor.")
        dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Origin", "X-CSRF-Token"],
    )
    application.add_middleware(CsrfOriginMiddleware)
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "İşlenmeyen API hatası.",
            extra={
                "http_method": request.method,
                "request_path": request.url.path,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "İşlem sırasında beklenmeyen bir sorun oluştu."},
        )

    return application


app = create_app()
