from __future__ import annotations

from src.state import AgentState


def planner_node(state: AgentState) -> AgentState:
    program = state.brief["program"]
    state.plan_steps = [
        {"name": "program_analysis", "objective": f"Interpret {program['use']} targets and zoning envelope."},
        {"name": "massing_generation", "objective": "Produce initial podium+tower massing commands."},
        {"name": "constraint_validation", "objective": "Check FAR, height, and coverage compliance."},
        {"name": "documentation", "objective": "Summarize decisions, risks, and fallback recommendations."},
    ]
    state.rationale_log.append("Planner created a 4-step workflow from brief requirements.")
    state.confidence_tags["planner"] = "high"
    return state
