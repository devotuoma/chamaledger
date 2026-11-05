from alembic import context

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.config import get_settings
from app.db import Base, build_engine

target_metadata = Base.metadata


def run() -> None:
    url = context.config.get_main_option("sqlalchemy.url") or get_settings().database_url
    with build_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run()
