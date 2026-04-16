"""Risk-assessor node.

Deterministic heuristics drive the final confidence tag (so retry/fallback
behavior remains auditable). When an LLM is available, we additionally ask
it for a short narrative summary and list of risk factors that land in the
rationale log and trace. If the LLM fails, the deterministic text is used.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.llm.client import LlmClient
from src.nodes.prompts import RISK_SYSTEM_PROMPT
from src.state import AgentState

NodeFn = Callable[[AgentState], AgentState]


def _deterministic_assessment(state: AgentState) -> tuple[str, str]:
    if state.errors:
        return ("Low confidence due to execution errors.", "low")
    if any(not r.get("is_feasible", False) for r in state.constraint_results):
        return (
            "Medium confidence; fallback/manual review advised due to infeasible constraints.",
            "medium",
        )
    return ("High confidence; brief appears feasible within stated assumptions.", "high")


def risk_assessor_node(state: AgentState) -> AgentState:
    summary, confidence = _deterministic_assessment(state)
    state.rationale_log.append(f"Risk assessor: {summary}")
    state.confidence_tags["risk_assessor"] = confidence
    state.status = "completed"
    return state


def make_risk_assessor_node(llm: LlmClient | None) -> NodeFn:
    if llm is None or not getattr(llm, "available", False):
        return risk_assessor_node

    def _node(state: AgentState) -> AgentState:
        heuristic_summary, heuristic_confidence = _deterministic_assessment(state)

        payload = {
            "brief_id": state.brief_id,
            "errors": state.errors,
            "retry_count": state.retry_count,
            "fallback_triggered": state.fallback_triggered,
            "constraint_results": state.constraint_results,
            "rationale_log": state.rationale_log[-8:],
        }

        response = llm.generate(
            RISK_SYSTEM_PROMPT,
            json.dumps(payload, indent=2),
            expect_json=True,
            retries=2,
        )

        summary = heuristic_summary
        risk_factors: list[str] = []
        used_llm = False
        fallback_reason: str | None = None

        if response.ok and isinstance(response.parsed, dict):
            llm_summary = str(response.parsed.get("summary", "")).strip()
            raw_factors = response.parsed.get("risk_factors", [])
            if llm_summary:
                summary = llm_summary
                used_llm = True
            if isinstance(raw_factors, list):
                risk_factors = [
                    str(f).strip() for f in raw_factors if str(f).strip()
                ][:4]
        else:
            fallback_reason = response.error or "LLM risk summary missing or malformed."

        # Confidence stays deterministic so retry/fallback semantics remain stable.
        state.confidence_tags["risk_assessor"] = heuristic_confidence

        log_line = f"Risk assessor: {summary}"
        if risk_factors:
            log_line += " Risk factors: " + "; ".join(risk_factors) + "."
        state.rationale_log.append(log_line)

        provenance: dict[str, Any] = {
            "node": "risk_assessor",
            "used_llm": used_llm,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "heuristic_confidence": heuristic_confidence,
        }
        if fallback_reason:
            provenance["fallback_reason"] = fallback_reason
        if risk_factors:
            provenance["risk_factors"] = risk_factors
        state.llm_provenance.append(provenance)

        state.status = "completed"
        return state

    return _node
