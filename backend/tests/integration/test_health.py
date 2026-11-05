import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base, engine

pytestmark = pytest.mark.integration


def test_health_reports_ok_when_database_is_reachable(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_migrations_match_the_models():
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
