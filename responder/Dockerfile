FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /srv
COPY pyproject.toml ./
COPY responder ./responder
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8100
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8100/health', timeout=2)"

CMD ["uvicorn", "--factory", "responder.main:create_app", "--host", "0.0.0.0", "--port", "8100"]
