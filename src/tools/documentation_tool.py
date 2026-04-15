from __future__ import annotations

from pydantic import BaseModel


class DocumentationToolInput(BaseModel):
    brief_id: str
    plan_steps: list[dict]
    generated_commands: list[dict]
    constraint_results: list[dict]
    rationale_log: list[str]
    confidence_tags: dict[str, str]
    fallback_triggered: bool


class DocumentationToolOutput(BaseModel):
    markdown: str


def run_documentation_tool(payload: DocumentationToolInput) -> DocumentationToolOutput:
    lines = [
        f"# DesignOps Agent Output — {payload.brief_id}",
        "",
        f"**Fallback triggered:** {'Yes' if payload.fallback_triggered else 'No'}",
        "",
        "## Plan Steps",
    ]
    for idx, step in enumerate(payload.plan_steps, start=1):
        lines.append(f"{idx}. {step.get('name')} — {step.get('objective')}")

    lines.extend(["", "## Generated Commands"])
    for cmd in payload.generated_commands:
        lines.append(f"- `{cmd.get('operation')}` with params `{cmd.get('params')}`")

    lines.extend(["", "## Constraint Results"])
    for result in payload.constraint_results:
        lines.append(f"- Feasible: `{result.get('is_feasible')}`")
        for v in result.get("violations", []):
            lines.append(f"  - Violation: {v}")
        for alt in result.get("alternatives", []):
            lines.append(f"  - Alternative: {alt}")

    lines.extend(["", "## Rationale Log"])
    for entry in payload.rationale_log:
        lines.append(f"- {entry}")

    lines.extend(["", "## Confidence Tags"])
    for step, confidence in payload.confidence_tags.items():
        lines.append(f"- `{step}`: **{confidence}**")

    return DocumentationToolOutput(markdown="\n".join(lines) + "\n")
