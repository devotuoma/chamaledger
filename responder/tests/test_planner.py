import json
from collections import Counter

import httpx

from responder.config import Settings
from responder.models import DISABLE_FAULT, ESCALATE, Evidence, Plan
from responder.planner import enforce_allowlist, make_plan, runbook_plan


def evidence(alert="ContributionsFailing", faults=(), errors=None):
    return Evidence(alert_name=alert, enabled_faults=list(faults), error_types=Counter(errors or {}))


def test_runbook_disables_the_fault_that_explains_the_alert():
    plan = runbook_plan(evidence(faults=["contribution_write_failure"]))
    assert (plan.action, plan.target) == (DISABLE_FAULT, "contribution_write_failure")


def test_runbook_matches_latency_faults_to_the_slow_alert_only():
    latency = ["contribution_write_latency"]
    assert runbook_plan(evidence("ContributionsSlow", latency)).action == DISABLE_FAULT
    assert runbook_plan(evidence("ContributionsFailing", latency)).action == ESCALATE


def test_runbook_escalates_and_names_what_it_saw_when_the_cause_is_unknown():
    plan = runbook_plan(evidence(errors={"OperationalError": 40}))
    assert plan.action == ESCALATE
    assert "OperationalError" in plan.reason


def test_allowlist_refuses_unknown_actions():
    plan = Plan(action="drop_database", target="members", planner="llm")
    assert enforce_allowlist(plan, evidence()).action == ESCALATE


def test_allowlist_refuses_a_fault_that_is_not_enabled():
    plan = Plan(action=DISABLE_FAULT, target="contribution_write_failure", planner="llm")
    assert enforce_allowlist(plan, evidence()).action == ESCALATE


def test_allowlist_refuses_an_enabled_but_unknown_flag():
    plan = Plan(action=DISABLE_FAULT, target="something_else", planner="llm")
    assert enforce_allowlist(plan, evidence(faults=["something_else"])).action == ESCALATE


def llm_settings():
    return Settings(llm_base_url="http://llm.test/v1", llm_api_key="k", llm_model="m")


def llm_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def replying(content):
    return lambda _: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


async def test_no_llm_configured_uses_the_runbook():
    async with llm_client(replying("{}")) as client:
        plan = await make_plan(Settings(), client, evidence(faults=["contribution_write_failure"]))
    assert plan.planner == "runbook"
    assert plan.action == DISABLE_FAULT


async def test_a_valid_llm_decision_is_used():
    reply = json.dumps(
        {"action": DISABLE_FAULT, "target": "contribution_write_failure", "reason": "flag is on"}
    )
    async with llm_client(replying(reply)) as client:
        plan = await make_plan(
            llm_settings(), client, evidence(faults=["contribution_write_failure"])
        )
    assert (plan.planner, plan.action) == ("llm", DISABLE_FAULT)


async def test_a_harmful_llm_decision_is_refused():
    reply = json.dumps({"action": "run_shell", "target": "rm -rf /", "reason": "trust me"})
    async with llm_client(replying(reply)) as client:
        plan = await make_plan(llm_settings(), client, evidence())
    assert plan.action == ESCALATE
    assert "Refused" in plan.reason


async def test_unparseable_llm_output_falls_back_to_the_runbook():
    async with llm_client(replying("I think you should panic")) as client:
        plan = await make_plan(
            llm_settings(), client, evidence(faults=["contribution_write_failure"])
        )
    assert (plan.planner, plan.action) == ("runbook", DISABLE_FAULT)


async def test_an_llm_outage_falls_back_to_the_runbook():
    async with llm_client(lambda _: httpx.Response(503)) as client:
        plan = await make_plan(llm_settings(), client, evidence())
    assert (plan.planner, plan.action) == ("runbook", ESCALATE)


async def test_only_technical_facts_are_sent_to_the_llm():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    case = evidence(errors={"ValueError": 1})
    case.sample_trace_ids = ["abc123"]
    async with llm_client(handler) as client:
        await make_plan(llm_settings(), client, case)
    sent = json.loads(seen["body"]["messages"][1]["content"])
    assert set(sent) == {
        "alert",
        "error_ratio",
        "p95_seconds",
        "enabled_faults",
        "error_types",
        "evidence_gaps",
    }
