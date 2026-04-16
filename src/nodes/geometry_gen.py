"""Geometry generation node.

LLM-first with a deterministic safety net. The deterministic tool
(``run_geometry_tool``) is always available for fallback so the agent
remains usable when Ollama is unreachable or returns an invalid payload.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.llm.client import LlmClient
from src.nodes.prompts import GEOMETRY_SYSTEM_PROMPT
from src.retry import with_retry
from src.state import AgentState
from src.tools.geometry_tool import (
    GeometryCommand,
    GeometryToolInput,
    GeometryToolOutput,
    run_geometry_tool,
)

NodeFn = Callable[[AgentState], AgentState]

ALLOWED_OPERATIONS = {"create_podium", "create_tower", "apply_setback"}


def geometry_gen_node(state: AgentState) -> AgentState:
    """Deterministic massing generation (original behavior)."""

    def _run() -> GeometryToolOutput:
        payload = GeometryToolInput(
            brief=state.brief,
            plan_steps=state.plan_steps,
            fallback_mode=state.fallback_triggered,
        )
        return run_geometry_tool(payload)

    output, errors = with_retry(_run, retries=2)
    if output is None:
        state.errors.extend(errors)
        state.generated_commands = []
        state.rationale_log.append("Geometry generation failed after retries.")
        state.confidence_tags["geometry_gen"] = "low"
    else:
        state.errors.extend(errors)
        state.generated_commands = [command.model_dump() for command in output.commands]
        state.rationale_log.append(output.rationale)
        state.confidence_tags["geometry_gen"] = (
            "medium" if state.fallback_triggered else "high"
        )
    return state


def make_geometry_gen_node(llm: LlmClient | None) -> NodeFn:
    """Return an LLM-first geometry node, or the deterministic node if no LLM."""
    if llm is None or not getattr(llm, "available", False):
        return geometry_gen_node

    def _node(state: AgentState) -> AgentState:
        user_prompt = json.dumps(
            {
                "brief": state.brief,
                "plan_steps": state.plan_steps,
                "fallback_mode": state.fallback_triggered,
                "previous_violations": _last_violations(state),
            },
            indent=2,
        )

        response = llm.generate(
            GEOMETRY_SYSTEM_PROMPT,
            user_prompt,
            expect_json=True,
            retries=2,
        )

        commands = _validate_llm_commands(response.parsed) if response.ok else None

        if commands is None:
            reason = response.error or "LLM geometry output failed schema validation."
            state.llm_provenance.append(
                {
                    "node": "geometry_gen",
                    "used_llm": False,
                    "fallback_reason": reason,
                    "latency_ms": response.latency_ms,
                    "model": response.model,
                }
            )
            state.rationale_log.append(
                f"Geometry generator fallback engaged — using deterministic tool ({reason})."
            )
            return geometry_gen_node(state)

        rationale = ""
        if isinstance(response.parsed, dict):
            rationale = str(response.parsed.get("rationale", "")).strip()

        state.generated_commands = [c.model_dump() for c in commands]
        state.rationale_log.append(
            f"Geometry generator (LLM) produced {len(commands)} commands."
            + (f" Rationale: {rationale}" if rationale else "")
        )
        state.confidence_tags["geometry_gen"] = (
            "medium" if state.fallback_triggered else "high"
        )
        state.llm_provenance.append(
            {
                "node": "geometry_gen",
                "used_llm": True,
                "model": response.model,
                "latency_ms": response.latency_ms,
                "commands_count": len(commands),
            }
        )
        return state

    return _node


def _last_violations(state: AgentState) -> list[str]:
    if not state.constraint_results:
        return []
    latest = state.constraint_results[-1]
    return list(latest.get("violations", []))


def _validate_llm_commands(parsed: Any) -> list[GeometryCommand] | None:
    """Validate and coerce LLM output into :class:`GeometryCommand` objects."""
    if not isinstance(parsed, dict):
        return None
    raw_commands = parsed.get("commands")
    if not isinstance(raw_commands, list) or not raw_commands:
        return None
    if not 1 <= len(raw_commands) <= 8:
        return None

    cleaned: list[GeometryCommand] = []
    for entry in raw_commands:
        if not isinstance(entry, dict):
            return None
        op = str(entry.get("operation", "")).strip()
        if op not in ALLOWED_OPERATIONS:
            return None
        params = entry.get("params", {})
        if not isinstance(params, dict) or not params:
            return None
        if not _numeric_params(params):
            return None
        if op == "apply_setback" and "setback_m" not in params:
            return None
        if op in {"create_podium", "create_tower"}:
            if "width_m" not in params or "depth_m" not in params:
                return None
            if "height_m" not in params and "floors" not in params:
                return None
        metadata = entry.get("metadata", {}) or {}
        if not isinstance(metadata, dict):
            return None
        try:
            cleaned.append(
                GeometryCommand(operation=op, params=params, metadata=metadata)
            )
        except Exception:  # noqa: BLE001 — Pydantic validation
            return None
    return cleaned


def _numeric_params(params: dict[str, Any]) -> bool:
    for value in params.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if value <= 0:
            return False
    return True
