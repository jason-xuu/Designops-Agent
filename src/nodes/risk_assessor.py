from __future__ import annotations

from src.state import AgentState


def risk_assessor_node(state: AgentState) -> AgentState:
    if state.errors:
        summary = "Low confidence due to execution errors."
        confidence = "low"
    elif any(not result.get("is_feasible", False) for result in state.constraint_results):
        summary = "Medium confidence; fallback/manual review advised due to infeasible constraints."
        confidence = "medium"
    else:
        summary = "High confidence; brief appears feasible within stated assumptions."
        confidence = "high"

    state.rationale_log.append(f"Risk assessor: {summary}")
    state.confidence_tags["risk_assessor"] = confidence
    state.status = "completed"
    return state
