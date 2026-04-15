from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GeometryToolInput(BaseModel):
    brief: dict[str, Any]
    plan_steps: list[dict[str, Any]]
    fallback_mode: bool = False


class GeometryCommand(BaseModel):
    operation: str
    params: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeometryToolOutput(BaseModel):
    commands: list[GeometryCommand]
    rationale: str


def run_geometry_tool(payload: GeometryToolInput) -> GeometryToolOutput:
    site = payload.brief["site"]
    program = payload.brief["program"]
    constraints = payload.brief["constraints"]
    lot_area = float(site["lot_area_sqm"])
    max_height = float(program["max_height_m"])
    floor_h = float(program["floor_to_floor_m"])
    target_far = float(program["target_far"])

    max_floors = max(1, int(max_height // floor_h))
    target_gfa = lot_area * target_far

    if payload.fallback_mode:
        reduced_far = min(target_far, 6.0)
        target_gfa = lot_area * reduced_far

    floor_area = target_gfa / max_floors
    footprint_area = min(floor_area, lot_area * float(constraints["max_site_coverage"]))
    side = round(footprint_area ** 0.5, 2)

    commands = [
        GeometryCommand(
            operation="create_podium",
            params={"width_m": side, "depth_m": side, "height_m": round(floor_h * 2, 2)},
            metadata={"stage": "base"},
        ),
        GeometryCommand(
            operation="create_tower",
            params={"width_m": round(side * 0.75, 2), "depth_m": round(side * 0.75, 2), "floors": max_floors - 2},
            metadata={"stage": "main_mass"},
        ),
        GeometryCommand(
            operation="apply_setback",
            params={"setback_m": float(site["setback_m"])},
            metadata={"stage": "compliance"},
        ),
    ]
    rationale = (
        f"Generated massing using FAR {target_far} over {max_floors} floors."
        + (" Fallback sizing applied." if payload.fallback_mode else "")
    )
    return GeometryToolOutput(commands=commands, rationale=rationale)
