"""Everything the agent can do to the outside world. There are no other write paths."""

import time
from collections import Counter

import httpx

from responder.config import Settings

JOURNEY = 'journey="record_contribution"'
ERROR_RATIO_QUERY = (
    f'(sum(rate(chama_journey_requests_total{{{JOURNEY},outcome="error"}}[1m])) or vector(0))'
    f" / sum(rate(chama_journey_requests_total{{{JOURNEY}}}[1m]))"
)
P95_QUERY = (
    "histogram_quantile(0.95, sum by (le) "
    f"(rate(chama_journey_duration_seconds_bucket{{{JOURNEY}}}[1m])))"
)
FAILED_LOGS_QUERY = '{service_name="chamaledger-api"} | outcome="error"'


class Tools:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        self._ops_headers = {"X-Ops-Token": settings.ops_token}

    async def _instant_query(self, query: str) -> list[dict]:
        response = await self.client.get(
            f"{self.settings.prometheus_url}/api/v1/query", params={"query": query}
        )
        response.raise_for_status()
        return response.json()["data"]["result"]

    async def _scalar(self, query: str) -> float | None:
        result = await self._instant_query(query)
        if not result:
            return None
        value = float(result[0]["value"][1])
        return None if value != value else value  # NaN means no traffic in the window.

    async def error_ratio(self) -> float | None:
        return await self._scalar(ERROR_RATIO_QUERY)

    async def p95_seconds(self) -> float | None:
        return await self._scalar(P95_QUERY)

    async def alert_is_firing(self, alert_name: str) -> bool:
        query = f'ALERTS{{alertname="{alert_name}",alertstate="firing"}}'
        return bool(await self._instant_query(query))

    async def recent_failures(self, minutes: int = 10) -> tuple[Counter, list[str]]:
        """Counts failed requests by error type, and returns some trace IDs to follow up."""
        response = await self.client.get(
            f"{self.settings.loki_url}/loki/api/v1/query_range",
            params={
                "query": FAILED_LOGS_QUERY,
                "start": str(int((time.time() - minutes * 60) * 1e9)),
                "limit": "200",
            },
        )
        response.raise_for_status()
        error_types: Counter = Counter()
        trace_ids: list[str] = []
        for stream in response.json()["data"]["result"]:
            labels = stream["stream"]
            error_types[labels.get("error_type", "unknown")] += len(stream["values"])
            trace_id = labels.get("trace_id")
            if trace_id and trace_id not in trace_ids:
                trace_ids.append(trace_id)
        return error_types, trace_ids[:5]

    async def enabled_faults(self) -> list[str]:
        response = await self.client.get(
            f"{self.settings.api_url}/api/ops/flags", headers=self._ops_headers
        )
        response.raise_for_status()
        return sorted(name for name, enabled in response.json().items() if enabled)

    async def disable_fault(self, name: str) -> None:
        response = await self.client.put(
            f"{self.settings.api_url}/api/ops/flags/{name}",
            headers=self._ops_headers,
            json={"enabled": False},
        )
        response.raise_for_status()

    async def probe(self) -> tuple[bool, float]:
        """Runs the real journey once. Returns whether it worked and how long it took."""
        started = time.perf_counter()
        try:
            response = await self.client.post(
                f"{self.settings.api_url}/api/ops/probe", headers=self._ops_headers
            )
            return response.status_code == 200, time.perf_counter() - started
        except httpx.HTTPError:
            return False, time.perf_counter() - started
