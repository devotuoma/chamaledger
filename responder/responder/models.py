from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

DISABLE_FAULT = "disable_fault"
ESCALATE = "escalate"


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Evidence:
    alert_name: str
    error_ratio: float | None = None
    p95_seconds: float | None = None
    enabled_faults: list[str] = field(default_factory=list)
    error_types: Counter = field(default_factory=Counter)
    sample_trace_ids: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        """Technical facts only. This is the one thing a remote planner gets to see."""
        return {
            "alert": self.alert_name,
            "error_ratio": self.error_ratio,
            "p95_seconds": self.p95_seconds,
            "enabled_faults": self.enabled_faults,
            "error_types": dict(self.error_types),
            "evidence_gaps": self.gaps,
        }


@dataclass
class Plan:
    action: str
    reason: str
    target: str | None = None
    planner: str = "runbook"


@dataclass
class Incident:
    id: str
    alert_name: str
    started_at: str
    status: str = "investigating"
    resolved_at: str | None = None
    plan: dict | None = None
    evidence: dict | None = None
    sample_trace_ids: list[str] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    issue_url: str | None = None

    def note(self, message: str) -> None:
        self.timeline.append({"at": utcnow(), "message": message})

    def to_dict(self) -> dict:
        return asdict(self)
