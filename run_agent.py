#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from src.agent import run_agent
from src.config import get_app_config
from src.state import AgentState
from src.store.sqlite_store import SqliteStore
from src.tools.documentation_tool import DocumentationToolInput, run_documentation_tool

console = Console()


def _load_brief(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DesignOps Agent on a design brief.")
    parser.add_argument(
        "--brief",
        choices=["residential", "mixed_use"],
        required=True,
        help="Brief id to run.",
    )
    args = parser.parse_args()

    app_cfg = get_app_config()
    brief_path = app_cfg.briefs_dir / f"brief_{args.brief}.json"
    brief = _load_brief(brief_path)

    run_id = str(uuid.uuid4())
    store = SqliteStore(app_cfg.sqlite_path)
    store.insert_run_start(run_id, args.brief)

    initial_state = AgentState(run_id=run_id, brief_id=args.brief, brief=brief)
    final_state = run_agent(initial_state, store=store)
    final_state.completed_at = datetime.now(UTC).isoformat()

    # Produce final markdown output from final state snapshot.
    doc_payload = DocumentationToolInput(
        brief_id=final_state.brief_id,
        plan_steps=final_state.plan_steps,
        generated_commands=final_state.generated_commands,
        constraint_results=final_state.constraint_results,
        rationale_log=final_state.rationale_log,
        confidence_tags=final_state.confidence_tags,
        fallback_triggered=final_state.fallback_triggered,
    )
    markdown = run_documentation_tool(doc_payload).markdown
    output_path = app_cfg.outputs_dir / f"{args.brief}_output.md"
    output_path.write_text(markdown, encoding="utf-8")

    trace_path = app_cfg.traces_dir / f"{args.brief}_trace.json"
    trace_path.write_text(json.dumps(final_state.model_dump(), indent=2), encoding="utf-8")

    store.complete_run(run_id, status=final_state.status)

    console.print(f"[green]Run complete[/green] — brief={args.brief}, run_id={run_id}")
    console.print(f"Trace: [cyan]{trace_path}[/cyan]")
    console.print(f"Output: [cyan]{output_path}[/cyan]")


if __name__ == "__main__":
    main()
