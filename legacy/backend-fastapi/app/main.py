"""FastAPI application factory and router registration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.dashboard_ws import router as dashboard_ws_router
from app.api.health import router as health_router
from app.api.inventory import router as inventory_router
from app.api.monitoring import router as monitoring_router
from app.api.procurement import router as procurement_router
from app.api.reports import router as reports_router
from app.api.search import router as search_router
from app.api.sales import router as sales_router
from app.core.config import settings
from app.services.inventory_events import register_inventory_event_handlers


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_inventory_event_handlers()
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(dashboard_ws_router)
    app.include_router(inventory_router)
    app.include_router(procurement_router)
    app.include_router(search_router)
    app.include_router(sales_router)
    app.include_router(reports_router)
    app.include_router(audit_router)
    app.include_router(monitoring_router)
    return app


app = create_app()
