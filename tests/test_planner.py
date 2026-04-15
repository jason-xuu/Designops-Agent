from src.nodes.planner import planner_node
from src.state import AgentState


def test_planner_produces_steps_and_confidence():
    state = AgentState(
        run_id="r1",
        brief_id="residential",
        brief={
            "program": {"use": "residential"},
            "site": {},
            "constraints": {},
        },
    )
    out = planner_node(state)
    assert len(out.plan_steps) >= 3
    assert out.confidence_tags["planner"] == "high"
    assert any("Planner created" in line for line in out.rationale_log)
