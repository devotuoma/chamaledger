from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health


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
    app.include_router(health.router, prefix="/api")
    return app


app = create_app()
