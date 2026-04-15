from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ConstraintToolInput(BaseModel):
    brief: dict[str, Any]
    commands: list[dict[str, Any]]


class ConstraintToolOutput(BaseModel):
    is_feasible: bool
    violations: list[str]
    alternatives: list[str]
    rationale: str


def run_constraint_tool(payload: ConstraintToolInput) -> ConstraintToolOutput:
    site = payload.brief["site"]
    program = payload.brief["program"]
    constraints = payload.brief["constraints"]

    lot_area = float(site["lot_area_sqm"])
    target_far = float(program["target_far"])
    max_height = float(program["max_height_m"])
    floor_h = float(program["floor_to_floor_m"])
    max_coverage = float(constraints["max_site_coverage"])

    max_floors = max(1, int(max_height // floor_h))
    max_buildable_gfa = lot_area * max_coverage * max_floors
    target_gfa = lot_area * target_far

    violations: list[str] = []
    alternatives: list[str] = []
    if target_gfa > max_buildable_gfa:
        violations.append(
            f"Target GFA {target_gfa:.0f} sqm exceeds max buildable GFA {max_buildable_gfa:.0f} sqm under height/coverage limits."
        )
        alternatives.extend(
            [
                "Lower FAR target to feasible range for current envelope.",
                "Increase height limit or reduce floor-to-floor heights.",
                "Pursue phased program split across adjacent sites.",
            ]
        )
    if not payload.commands:
        violations.append("No geometry commands generated for validation.")

    is_feasible = len(violations) == 0
    rationale = "Constraint checks passed." if is_feasible else "Constraint checks found infeasibility that requires fallback."
    return ConstraintToolOutput(
        is_feasible=is_feasible,
        violations=violations,
        alternatives=alternatives,
        rationale=rationale,
    )
