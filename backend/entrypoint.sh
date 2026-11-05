#!/bin/sh
set -e
alembic upgrade head
if [ "$SEED_DEMO" = "true" ]; then
  python -m app.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
