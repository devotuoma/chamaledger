from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    """Hosting providers hand out postgres:// URLs; SQLAlchemy needs the driver named."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def build_engine(url: str) -> Engine:
    url = normalize_url(url)
    if url.startswith("sqlite"):
        engine = create_engine(
            url, hide_parameters=True, connect_args={"check_same_thread": False}
        )

        # The sqlite driver manages transactions in a way that breaks savepoints, which the
        # journey probe depends on. These hooks hand control back to SQLAlchemy.
        @event.listens_for(engine, "connect")
        def _disable_driver_transactions(connection, _record):
            connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def _emit_begin(connection):
            connection.exec_driver_sql("BEGIN")

        return engine
    # hide_parameters keeps customer values out of error messages, and so out of telemetry.
    return create_engine(
        url,
        hide_parameters=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
    )


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
