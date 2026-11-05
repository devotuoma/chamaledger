from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    api_url: str = "http://api:8000"
    prometheus_url: str = "http://prometheus:9090"
    loki_url: str = "http://loki:3100"
    ops_token: str = "local-ops-token"
    responder_token: str = "local-responder-token"

    incident_dir: str = "/tmp/incidents"
    probe_interval_seconds: float = 5
    probe_enabled: bool = True
    verify_timeout_seconds: float = 420
    verify_poll_seconds: float = 10
    healthy_probes_required: int = 3

    # Optional. Any OpenAI-compatible chat completions endpoint can act as the planner.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # Optional. When both are set, each incident is also filed as a GitHub issue.
    github_token: str = ""
    github_repository: str = ""
