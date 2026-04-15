from __future__ import annotations

from src.state import AgentState
from src.tools.documentation_tool import DocumentationToolInput, run_documentation_tool


def doc_writer_node(state: AgentState) -> AgentState:
    payload = DocumentationToolInput(
        brief_id=state.brief_id,
        plan_steps=state.plan_steps,
        generated_commands=state.generated_commands,
        constraint_results=state.constraint_results,
        rationale_log=state.rationale_log,
        confidence_tags=state.confidence_tags,
        fallback_triggered=state.fallback_triggered,
    )
    output = run_documentation_tool(payload)
    state.rationale_log.append("Documentation writer produced markdown handoff output.")
    state.confidence_tags["doc_writer"] = "high"
    state.step_traces.append({"node": "doc_writer", "markdown": output.markdown})
    return state
