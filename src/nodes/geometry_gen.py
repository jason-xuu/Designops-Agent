from __future__ import annotations

from src.retry import with_retry
from src.state import AgentState
from src.tools.geometry_tool import GeometryToolInput, run_geometry_tool


def geometry_gen_node(state: AgentState) -> AgentState:
    def _run():
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
        state.confidence_tags["geometry_gen"] = "medium" if state.fallback_triggered else "high"
    return state
