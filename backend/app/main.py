from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.logs import configure_logging
from app.routers import contributions, dashboard, health, loans, members, ops
from app.telemetry import API_PREFIX, add_observability_middleware, configure_telemetry


def create_app() -> FastAPI:
    settings = get_settings()
    log_handler = configure_logging(settings.log_level)
    app = FastAPI(title="ChamaLedger API", version="1.0.0")
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins.split(","),
            allow_methods=["*"],
            allow_headers=["*"],
        )
    add_observability_middleware(app)
    register_error_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(members.router, prefix=API_PREFIX)
    app.include_router(contributions.router, prefix=API_PREFIX)
    app.include_router(loans.router, prefix=API_PREFIX)
    app.include_router(dashboard.router, prefix=API_PREFIX)
    app.include_router(ops.router, prefix=API_PREFIX)
    configure_telemetry(app, settings, log_handler)
    return app


app = create_app()
