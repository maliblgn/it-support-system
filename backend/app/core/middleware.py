import hmac

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CsrfOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)

        settings = get_settings()
        origin = request.headers.get("origin")
        allowed_origins = {value.rstrip("/") for value in settings.cors_origins}
        if origin and origin.rstrip("/") not in allowed_origins:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "İstek kaynağına izin verilmiyor."},
            )

        session_cookie = request.cookies.get(settings.session_cookie_name)
        if session_cookie:
            csrf_cookie = request.cookies.get(settings.csrf_cookie_name, "")
            csrf_header = request.headers.get("X-CSRF-Token", "")
            if not csrf_cookie or not csrf_header or not hmac.compare_digest(
                csrf_cookie, csrf_header
            ):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF doğrulaması başarısız."},
                )

        return await call_next(request)
