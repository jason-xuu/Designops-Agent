from src.nodes.risk_assessor import make_risk_assessor_node, risk_assessor_node
from src.state import AgentState
from tests._fake_llm import FakeLlmClient


def _state(feasible: bool = True, errors=None) -> AgentState:
    return AgentState(
        run_id="r-risk",
        brief_id="residential",
        brief={"program": {"use": "residential"}, "site": {}, "constraints": {}},
        constraint_results=[{"is_feasible": feasible, "violations": [], "alternatives": []}],
        errors=errors or [],
    )


def test_heuristic_confidence_remains_stable_when_llm_succeeds():
    llm = FakeLlmClient(
        payloads=[
            {
                "summary": "All constraints comfortably satisfied.",
                "confidence": "high",
                "risk_factors": ["Schedule buffer tight"],
            }
        ]
    )
    node = make_risk_assessor_node(llm)
    out = node(_state(feasible=True))

    assert out.confidence_tags["risk_assessor"] == "high"
    assert out.status == "completed"
    # LLM narrative must reach the rationale log.
    assert any("comfortably satisfied" in line for line in out.rationale_log)
    assert out.llm_provenance[-1]["used_llm"] is True


def test_llm_failure_falls_back_to_heuristic_text():
    llm = FakeLlmClient(payloads=[None], errors=["connection refused"])
    node = make_risk_assessor_node(llm)
    out = node(_state(feasible=False))

    assert out.confidence_tags["risk_assessor"] == "medium"
    # Heuristic summary text must appear in rationale.
    assert any("Medium confidence" in line for line in out.rationale_log)
    assert out.llm_provenance[-1]["used_llm"] is False
    assert "connection refused" in out.llm_provenance[-1]["fallback_reason"]


def test_unavailable_llm_returns_deterministic_node():
    llm = FakeLlmClient(available=False)
    node = make_risk_assessor_node(llm)
    assert node is risk_assessor_node
