import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

# Must be set before anything imports app.db, which builds its engine on import.
_tmp = tempfile.mkdtemp(prefix="chamaledger-test-")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def schema() -> Iterator[None]:
    """Build the schema through the real migrations, not create_all."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables(schema: None) -> Iterator[None]:
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session() -> Iterator[Session]:
    with SessionLocal() as db_session:
        yield db_session
