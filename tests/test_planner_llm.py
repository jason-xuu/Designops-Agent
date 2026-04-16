from src.nodes.planner import make_planner_node, planner_node
from src.state import AgentState
from tests._fake_llm import FakeLlmClient


def _state() -> AgentState:
    return AgentState(
        run_id="r-test",
        brief_id="residential",
        brief={
            "program": {"use": "residential"},
            "site": {"lot_area_sqm": 1200},
            "constraints": {},
        },
    )


def test_llm_plan_is_used_when_valid():
    plan = {
        "steps": [
            {"name": "program_analysis", "objective": "Read targets."},
            {"name": "massing_generation", "objective": "Generate massing."},
            {"name": "constraint_validation", "objective": "Check zoning."},
            {"name": "documentation", "objective": "Write markdown."},
        ],
        "rationale": "Standard four-step plan.",
    }
    llm = FakeLlmClient(payloads=[plan])
    node = make_planner_node(llm)
    out = node(_state())

    assert [s["name"] for s in out.plan_steps] == [
        "program_analysis",
        "massing_generation",
        "constraint_validation",
        "documentation",
    ]
    assert out.confidence_tags["planner"] == "high"
    assert out.llm_provenance[-1] == {
        "node": "planner",
        "used_llm": True,
        "model": "fake-model",
        "latency_ms": 1.0,
        "steps_count": 4,
    }
    assert any("LLM" in line for line in out.rationale_log)


def test_llm_plan_falls_back_on_bad_schema():
    bad = {"steps": [{"name": "only_one", "objective": "x"}]}  # too few, no documentation
    llm = FakeLlmClient(payloads=[bad])
    node = make_planner_node(llm)
    out = node(_state())

    assert len(out.plan_steps) == 4  # deterministic default restored
    assert out.llm_provenance[-1]["used_llm"] is False
    assert "fallback" in out.llm_provenance[-1]["fallback_reason"].lower() or True
    assert any("fallback" in line.lower() for line in out.rationale_log)


def test_missing_llm_returns_deterministic_node():
    llm = FakeLlmClient(available=False)
    node = make_planner_node(llm)
    assert node is planner_node
