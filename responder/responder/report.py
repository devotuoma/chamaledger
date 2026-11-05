import json
from pathlib import Path

import httpx

from responder.config import Settings
from responder.models import Incident


def render_markdown(incident: Incident) -> str:
    plan = incident.plan or {}
    evidence = incident.evidence or {}
    timeline = "\n".join(f"- `{e['at']}` {e['message']}" for e in incident.timeline)
    traces = (
        "\n".join(f"- `{trace_id}`" for trace_id in incident.sample_trace_ids) or "- none found"
    )
    return f"""# Incident {incident.id}: {incident.alert_name}

| | |
| --- | --- |
| Status | **{incident.status}** |
| Started | {incident.started_at} |
| Finished | {incident.resolved_at or "ongoing"} |
| Action | `{plan.get("action")}` on `{plan.get("target")}` |
| Decided by | {plan.get("planner")} planner |

## Reasoning

{plan.get("reason", "No plan was made.")}

## Evidence

```json
{json.dumps(evidence, indent=2)}
```

## Sample traces of failed requests

{traces}

## Timeline

{timeline}
"""


def save_report(settings: Settings, incident: Incident) -> Path:
    directory = Path(settings.incident_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{incident.id}.md"
    path.write_text(render_markdown(incident))
    (directory / f"{incident.id}.json").write_text(json.dumps(incident.to_dict(), indent=2))
    return path


async def file_github_issue(
    settings: Settings, client: httpx.AsyncClient, incident: Incident
) -> str | None:
    if not (settings.github_token and settings.github_repository):
        return None
    response = await client.post(
        f"https://api.github.com/repos/{settings.github_repository}/issues",
        headers={
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": f"[{incident.status}] {incident.alert_name} ({incident.id})",
            "body": render_markdown(incident),
        },
    )
    response.raise_for_status()
    return response.json()["html_url"]
