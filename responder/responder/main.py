import asyncio
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from responder.agent import Agent
from responder.config import Settings
from responder.tools import Tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
# httpx logs full request URLs at INFO, and they add nothing here.
logging.getLogger("httpx").setLevel(logging.WARNING)


class Alert(BaseModel):
    status: str
    labels: dict[str, str]


class AlertmanagerWebhook(BaseModel):
    alerts: list[Alert]


class ProbeState:
    success = 1
    duration = 0.0


async def probe_forever(tools: Tools, state: ProbeState, interval: float) -> None:
    while True:
        ok, duration = await tools.probe()
        state.success, state.duration = int(ok), duration
        await asyncio.sleep(interval)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(timeout=15) as client:
            tools = Tools(settings, client)
            app.state.agent = Agent(settings, client, tools)
            app.state.probe = ProbeState()
            prober = None
            if settings.probe_enabled:
                prober = asyncio.create_task(
                    probe_forever(tools, app.state.probe, settings.probe_interval_seconds)
                )
            yield
            if prober:
                prober.cancel()

    app = FastAPI(title="ChamaLedger Responder", lifespan=lifespan)

    def require_token(authorization: str = Header(default="")) -> None:
        expected = f"Bearer {settings.responder_token}"
        if not hmac.compare_digest(authorization.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="Invalid token")

    @app.post("/alerts", dependencies=[Depends(require_token)])
    async def receive_alerts(webhook: AlertmanagerWebhook, request: Request) -> dict[str, list[str]]:
        agent: Agent = request.app.state.agent
        started = []
        for alert in webhook.alerts:
            name = alert.labels.get("alertname", "unknown")
            if alert.status == "resolved":
                agent.on_alert_resolved(name)
                continue
            incident = agent.wake(name)
            if incident:
                started.append(incident.id)
        return {"started": started}

    @app.get("/incidents")
    async def incidents(request: Request) -> list[dict]:
        return [incident.to_dict() for incident in request.app.state.agent.incidents]

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics(request: Request) -> str:
        probe: ProbeState = request.app.state.probe
        return (
            "# TYPE chama_probe_success gauge\n"
            f"chama_probe_success {probe.success}\n"
            "# TYPE chama_probe_duration_seconds gauge\n"
            f"chama_probe_duration_seconds {probe.duration}\n"
        )

    return app


app = create_app
