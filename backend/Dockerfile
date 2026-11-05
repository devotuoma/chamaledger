FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY alembic.ini entrypoint.sh ./
COPY migrations ./migrations

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=10 \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/health', timeout=2)"

ENTRYPOINT ["sh", "entrypoint.sh"]
