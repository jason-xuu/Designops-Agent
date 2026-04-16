"""Planner node.

Two entry points:

* :func:`planner_node` — deterministic fallback, preserves the v0.3 contract
  that the unit tests depend on.
* :func:`make_planner_node` — LLM-first wrapper; on any LLM/parse failure
  it delegates to the deterministic implementation and records the reason
  in :attr:`AgentState.llm_provenance`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.llm.client import LlmClient
from src.nodes.prompts import PLANNER_SYSTEM_PROMPT
from src.state import AgentState

NodeFn = Callable[[AgentState], AgentState]

DEFAULT_PLAN_STEPS = [
    {
        "name": "program_analysis",
        "objective": "Interpret program targets and zoning envelope from the brief.",
    },
    {
        "name": "massing_generation",
        "objective": "Produce initial podium+tower massing commands.",
    },
    {
        "name": "constraint_validation",
        "objective": "Check FAR, height, and coverage compliance.",
    },
    {
        "name": "documentation",
        "objective": "Summarize decisions, risks, and fallback recommendations.",
    },
]


def planner_node(state: AgentState) -> AgentState:
    """Deterministic 4-step plan derived from the brief's program."""
    program = state.brief["program"]
    use = program.get("use", "project")
    steps = [dict(step) for step in DEFAULT_PLAN_STEPS]
    steps[0]["objective"] = f"Interpret {use} targets and zoning envelope."
    state.plan_steps = steps
    state.rationale_log.append("Planner created a 4-step workflow from brief requirements.")
    state.confidence_tags["planner"] = "high"
    return state


def make_planner_node(llm: LlmClient | None) -> NodeFn:
    """Return a planner node that tries ``llm`` first, then falls back."""
    if llm is None or not getattr(llm, "available", False):
        return planner_node

    def _node(state: AgentState) -> AgentState:
        user_prompt = json.dumps(
            {
                "brief_id": state.brief_id,
                "program": state.brief.get("program", {}),
                "site": state.brief.get("site", {}),
                "constraints": state.brief.get("constraints", {}),
            },
            indent=2,
        )

        response = llm.generate(
            PLANNER_SYSTEM_PROMPT,
            user_prompt,
            expect_json=True,
            retries=2,
        )

        steps = _validate_llm_plan(response.parsed) if response.ok else None

        if steps is None:
            reason = response.error or "LLM plan failed schema validation."
            state.llm_provenance.append(
                {
                    "node": "planner",
                    "used_llm": False,
                    "fallback_reason": reason,
                    "latency_ms": response.latency_ms,
                    "model": response.model,
                }
            )
            state.rationale_log.append(
                f"Planner fallback engaged — using deterministic plan ({reason})."
            )
            return planner_node(state)

        rationale = ""
        if isinstance(response.parsed, dict):
            rationale = str(response.parsed.get("rationale", "")).strip()

        state.plan_steps = steps
        state.confidence_tags["planner"] = "high"
        state.rationale_log.append(
            f"Planner (LLM) produced {len(steps)} steps."
            + (f" Rationale: {rationale}" if rationale else "")
        )
        state.llm_provenance.append(
            {
                "node": "planner",
                "used_llm": True,
                "model": response.model,
                "latency_ms": response.latency_ms,
                "steps_count": len(steps),
            }
        )
        return state

    return _node


def _validate_llm_plan(parsed: Any) -> list[dict[str, Any]] | None:
    """Return a validated plan list, or ``None`` if the payload is bad."""
    if not isinstance(parsed, dict):
        return None
    raw_steps = parsed.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        return None

    cleaned: list[dict[str, Any]] = []
    for entry in raw_steps:
        if not isinstance(entry, dict):
            return None
        name = str(entry.get("name", "")).strip()
        objective = str(entry.get("objective", "")).strip()
        if not name or not objective:
            return None
        cleaned.append({"name": name, "objective": objective})

    if not 3 <= len(cleaned) <= 6:
        return None
    if cleaned[-1]["name"] != "documentation":
        return None
    if not any(step["name"] == "massing_generation" for step in cleaned):
        return None
    return cleaned
