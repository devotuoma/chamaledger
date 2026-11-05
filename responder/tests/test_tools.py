"""The real HTTP layer. Agent tests use fakes, so requests must be checked here."""

import json

import httpx
import pytest

from responder.config import Settings
from responder.tools import ERROR_RATIO_QUERY, Tools


def tools_with(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return Tools(Settings(ops_token="secret"), client)


async def test_disable_fault_sends_a_request_the_api_can_parse():
    seen = {}

    def handler(request):
        seen.update(
            method=request.method,
            path=request.url.path,
            token=request.headers["X-Ops-Token"],
            content_type=request.headers["Content-Type"],
            body=json.loads(request.content),
        )
        return httpx.Response(200, json={})

    await tools_with(handler).disable_fault("contribution_write_failure")
    assert seen == {
        "method": "PUT",
        "path": "/api/ops/flags/contribution_write_failure",
        "token": "secret",
        "content_type": "application/json",
        "body": {"enabled": False},
    }


async def test_disable_fault_raises_when_the_api_refuses():
    tools = tools_with(lambda _: httpx.Response(422))
    with pytest.raises(httpx.HTTPStatusError):
        await tools.disable_fault("contribution_write_failure")


async def test_enabled_faults_lists_only_the_ones_that_are_on():
    tools = tools_with(lambda _: httpx.Response(200, json={"a": True, "b": False}))
    assert await tools.enabled_faults() == ["a"]


async def test_no_traffic_reads_as_no_value_rather_than_as_a_number():
    body = {"data": {"result": [{"value": [0, "NaN"]}]}}
    assert await tools_with(lambda _: httpx.Response(200, json=body)).error_ratio() is None


def test_error_ratio_query_divides_the_whole_numerator():
    assert ERROR_RATIO_QUERY.startswith("(sum(rate(")
    assert "or vector(0)) / sum(" in ERROR_RATIO_QUERY


async def test_recent_failures_groups_by_type_and_collects_traces():
    streams = [
        {"stream": {"error_type": "Boom", "trace_id": "t1"}, "values": [["1", "a"], ["2", "b"]]},
        {"stream": {"error_type": "Boom", "trace_id": "t2"}, "values": [["3", "c"]]},
        {"stream": {"trace_id": "t1"}, "values": [["4", "d"]]},
    ]
    body = {"data": {"result": streams}}
    errors, traces = await tools_with(lambda _: httpx.Response(200, json=body)).recent_failures()
    assert errors == {"Boom": 3, "unknown": 1}
    assert traces == ["t1", "t2"]


async def test_probe_reports_a_failure_instead_of_raising():
    def refuse(_):
        raise httpx.ConnectError("api is down")

    ok, _ = await tools_with(refuse).probe()
    assert ok is False
    ok, _ = await tools_with(lambda _: httpx.Response(500)).probe()
    assert ok is False
    ok, _ = await tools_with(lambda _: httpx.Response(200)).probe()
    assert ok is True
