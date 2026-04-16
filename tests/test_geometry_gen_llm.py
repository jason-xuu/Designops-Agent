from src.nodes.geometry_gen import geometry_gen_node, make_geometry_gen_node
from src.state import AgentState
from tests._fake_llm import FakeLlmClient


def _state(fallback: bool = False) -> AgentState:
    return AgentState(
        run_id="r-geo",
        brief_id="residential",
        brief={
            "site": {"lot_area_sqm": 2400, "setback_m": 5},
            "program": {
                "use": "residential",
                "target_far": 3.0,
                "max_height_m": 36,
                "floor_to_floor_m": 3.0,
            },
            "constraints": {"max_site_coverage": 0.65},
        },
        fallback_triggered=fallback,
    )


def test_llm_geometry_commands_are_used_when_valid():
    payload = {
        "commands": [
            {
                "operation": "create_podium",
                "params": {"width_m": 30.0, "depth_m": 30.0, "height_m": 6.0},
                "metadata": {"stage": "base"},
            },
            {
                "operation": "create_tower",
                "params": {"width_m": 22.0, "depth_m": 22.0, "floors": 10},
                "metadata": {"stage": "main_mass"},
            },
            {
                "operation": "apply_setback",
                "params": {"setback_m": 5.0},
                "metadata": {"stage": "compliance"},
            },
        ],
        "rationale": "Podium-tower with 5m setback.",
    }
    llm = FakeLlmClient(payloads=[payload])
    node = make_geometry_gen_node(llm)
    out = node(_state())

    assert len(out.generated_commands) == 3
    ops = [c["operation"] for c in out.generated_commands]
    assert ops == ["create_podium", "create_tower", "apply_setback"]
    assert out.confidence_tags["geometry_gen"] == "high"
    assert out.llm_provenance[-1]["used_llm"] is True
    assert out.llm_provenance[-1]["commands_count"] == 3


def test_unknown_operation_triggers_fallback():
    bad = {
        "commands": [
            {"operation": "teleport_building", "params": {"x_m": 1}, "metadata": {}},
        ],
        "rationale": "nope",
    }
    llm = FakeLlmClient(payloads=[bad])
    node = make_geometry_gen_node(llm)
    out = node(_state())

    assert len(out.generated_commands) == 3  # deterministic fallback produces 3 cmds
    assert out.llm_provenance[-1]["used_llm"] is False
    assert any("fallback" in line.lower() for line in out.rationale_log)


def test_non_numeric_params_trigger_fallback():
    bad = {
        "commands": [
            {
                "operation": "create_podium",
                "params": {"width_m": "thirty", "depth_m": 30, "height_m": 6},
                "metadata": {},
            },
        ],
    }
    llm = FakeLlmClient(payloads=[bad])
    node = make_geometry_gen_node(llm)
    out = node(_state())
    assert len(out.generated_commands) == 3
    assert out.llm_provenance[-1]["used_llm"] is False


def test_unavailable_llm_uses_deterministic_node():
    llm = FakeLlmClient(available=False)
    node = make_geometry_gen_node(llm)
    assert node is geometry_gen_node
