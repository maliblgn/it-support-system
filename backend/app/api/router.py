from fastapi import APIRouter

from app.api.routes import (
    admin,
    attachments,
    auth,
    health,
    it_tickets,
    notifications,
    operations,
    ratings,
    reports,
    system,
    tickets,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(ratings.router, prefix="/tickets", tags=["ticket-ratings"])
api_router.include_router(attachments.router, prefix="/tickets", tags=["attachments"])
api_router.include_router(it_tickets.router, prefix="/it/tickets", tags=["it-tickets"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(operations.router, tags=["ticket-operations"])
api_router.include_router(reports.router, prefix="/it/reports", tags=["it-reports"])
api_router.include_router(system.router, prefix="/it/system", tags=["it-system"])
