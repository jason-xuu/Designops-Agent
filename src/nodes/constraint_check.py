from __future__ import annotations

from src.state import AgentState
from src.tools.constraint_tool import ConstraintToolInput, run_constraint_tool


def constraint_check_node(state: AgentState) -> AgentState:
    payload = ConstraintToolInput(brief=state.brief, commands=state.generated_commands)
    output = run_constraint_tool(payload)
    result = output.model_dump()
    state.constraint_results.append(result)
    state.rationale_log.append(output.rationale)
    state.confidence_tags["constraint_check"] = "high" if output.is_feasible else "low"

    if not output.is_feasible and state.retry_count < 2:
        state.retry_count += 1
        state.fallback_triggered = True
        state.rationale_log.append(
            f"Retry path triggered ({state.retry_count}/2). Generating simplified fallback massing."
        )
    elif not output.is_feasible:
        state.rationale_log.append("Max retries reached. Marking run for manual review.")
    return state
