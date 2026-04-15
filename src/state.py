from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]


class AgentState(BaseModel):
    run_id: str
    brief_id: str
    brief: dict[str, Any]
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    status: str = "running"

    plan_steps: list[dict[str, Any]] = Field(default_factory=list)
    generated_commands: list[dict[str, Any]] = Field(default_factory=list)
    constraint_results: list[dict[str, Any]] = Field(default_factory=list)
    rationale_log: list[str] = Field(default_factory=list)
    confidence_tags: dict[str, Confidence] = Field(default_factory=dict)
    retry_count: int = 0
    errors: list[str] = Field(default_factory=list)
    fallback_triggered: bool = False

    step_traces: list[dict[str, Any]] = Field(default_factory=list)
