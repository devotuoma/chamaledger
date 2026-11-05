import asyncio
import logging
import time
import uuid

import httpx

from responder.config import Settings
from responder.models import DISABLE_FAULT, Evidence, Incident, Plan, utcnow
from responder.planner import make_plan
from responder.report import file_github_issue, save_report
from responder.tools import Tools

logger = logging.getLogger("responder.agent")

SLOW_SECONDS = 1.0


class Agent:
    def __init__(self, settings: Settings, client: httpx.AsyncClient, tools: Tools) -> None:
        self.settings = settings
        self.client = client
        self.tools = tools
        self.incidents: list[Incident] = []
        self._running: asyncio.Task | None = None
        # Escalated alerts stay quiet until Alertmanager reports them resolved.
        self._escalated: set[str] = set()

    def on_alert_resolved(self, alert_name: str) -> None:
        self._escalated.discard(alert_name)

    def wake(self, alert_name: str) -> Incident | None:
        """Starts an incident, unless one is running or this alert already went to a human."""
        if self._running is not None and not self._running.done():
            logger.info("Incident already running, ignoring repeat of %s", alert_name)
            return None
        if alert_name in self._escalated:
            logger.info("%s already escalated, ignoring repeat", alert_name)
            return None
        incident = Incident(
            id=f"INC-{uuid.uuid4().hex[:8]}", alert_name=alert_name, started_at=utcnow()
        )
        self.incidents.append(incident)
        self._running = asyncio.create_task(self.respond(incident))
        return incident

    async def investigate(self, alert_name: str) -> Evidence:
        """Failure of one source leaves a recorded gap, and never stops the investigation."""
        evidence = Evidence(alert_name=alert_name)

        async def gather(name, call, apply):
            try:
                apply(await call())
            except (httpx.HTTPError, KeyError, ValueError) as error:
                evidence.gaps.append(f"{name} unavailable: {type(error).__name__}")

        def set_failures(result):
            evidence.error_types, evidence.sample_trace_ids = result

        await gather("error ratio", self.tools.error_ratio, lambda v: setattr(evidence, "error_ratio", v))
        await gather("p95", self.tools.p95_seconds, lambda v: setattr(evidence, "p95_seconds", v))
        await gather("logs", self.tools.recent_failures, set_failures)
        await gather("flags", self.tools.enabled_faults, lambda v: setattr(evidence, "enabled_faults", v))
        return evidence

    async def act(self, plan: Plan) -> None:
        if plan.action == DISABLE_FAULT:
            await self.tools.disable_fault(plan.target)

    async def verify(self, incident: Incident) -> bool:
        """Recovered means the journey works from outside and the real alert has cleared."""
        deadline = time.monotonic() + self.settings.verify_timeout_seconds
        healthy = 0
        probes_noted = False
        while time.monotonic() < deadline:
            ok, duration = await self.tools.probe()
            healthy = healthy + 1 if ok and duration < SLOW_SECONDS else 0
            if healthy >= self.settings.healthy_probes_required:
                if not probes_noted:
                    incident.note(f"{healthy} consecutive probes healthy, waiting for the alert")
                    probes_noted = True
                try:
                    if not await self.tools.alert_is_firing(incident.alert_name):
                        return True
                except httpx.HTTPError as error:
                    incident.note(f"Could not read alert state: {type(error).__name__}")
            await asyncio.sleep(self.settings.verify_poll_seconds)
        return False

    async def respond(self, incident: Incident) -> None:
        try:
            incident.note(f"Woken by {incident.alert_name}")
            evidence = await self.investigate(incident.alert_name)
            incident.evidence = evidence.summary()
            incident.sample_trace_ids = evidence.sample_trace_ids
            incident.note(
                f"Investigated: error ratio {evidence.error_ratio}, p95 {evidence.p95_seconds}, "
                f"flags {evidence.enabled_faults}, errors {dict(evidence.error_types)}"
            )

            plan = await make_plan(self.settings, self.client, evidence)
            incident.plan = vars(plan)
            incident.note(f"Plan from {plan.planner}: {plan.action} {plan.target or ''}. {plan.reason}")

            if plan.action != DISABLE_FAULT:
                self._escalate(incident, "Needs a human")
            else:
                await self.act(plan)
                incident.note(f"Disabled {plan.target}, verifying recovery")
                if await self.verify(incident):
                    incident.status = "resolved"
                    incident.note("Recovery verified: journey healthy and alert cleared")
                else:
                    self._escalate(incident, "The fix did not restore the journey in time")
        except Exception as error:  # noqa: BLE001 (a crashed agent must still hand over)
            logger.exception("Responder failed")
            self._escalate(incident, f"Agent error: {type(error).__name__}")
        finally:
            incident.resolved_at = utcnow()
            await self._publish(incident)

    def _escalate(self, incident: Incident, why: str) -> None:
        incident.status = "escalated"
        self._escalated.add(incident.alert_name)
        incident.note(f"Escalated to the human lead. {why}")

    async def _publish(self, incident: Incident) -> None:
        try:
            incident.issue_url = await file_github_issue(self.settings, self.client, incident)
        except httpx.HTTPError as error:
            incident.note(f"Could not file a GitHub issue: {type(error).__name__}")
        save_report(self.settings, incident)
        logger.info("Incident %s finished: %s", incident.id, incident.status)
