from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.routers import contributions, dashboard, health, loans, members


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ChamaLedger API", version="1.0.0")
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins.split(","),
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(members.router, prefix="/api")
    app.include_router(contributions.router, prefix="/api")
    app.include_router(loans.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    return app


app = create_app()
