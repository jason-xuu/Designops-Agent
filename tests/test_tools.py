from src.tools.constraint_tool import ConstraintToolInput, run_constraint_tool
from src.tools.geometry_tool import GeometryToolInput, run_geometry_tool


def test_geometry_tool_returns_nl2geo_style_commands():
    payload = GeometryToolInput(
        brief={
            "site": {"lot_area_sqm": 2400, "setback_m": 5},
            "program": {"target_far": 3.0, "max_height_m": 36, "floor_to_floor_m": 3.0},
            "constraints": {"max_site_coverage": 0.65},
        },
        plan_steps=[{"name": "massing_generation"}],
    )
    out = run_geometry_tool(payload)
    assert len(out.commands) >= 1
    assert {"operation", "params", "metadata"}.issubset(out.commands[0].model_dump().keys())


def test_constraint_tool_flags_infeasible_far():
    payload = ConstraintToolInput(
        brief={
            "site": {"lot_area_sqm": 1200},
            "program": {"target_far": 15, "max_height_m": 20, "floor_to_floor_m": 3.5},
            "constraints": {"max_site_coverage": 0.7},
        },
        commands=[{"operation": "create_tower"}],
    )
    out = run_constraint_tool(payload)
    assert out.is_feasible is False
    assert out.violations
    assert out.alternatives
