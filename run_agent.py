#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from src.agent import run_agent
from src.config import get_app_config, get_llm_config
from src.llm import create_llm_client
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
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Force deterministic fallback path (skip the Ollama LLM).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    app_cfg = get_app_config()
    brief_path = app_cfg.briefs_dir / f"brief_{args.brief}.json"
    brief = _load_brief(brief_path)

    if args.no_llm:
        from src.llm.noop_client import NoopLlmClient

        llm = NoopLlmClient()
        console.print("[yellow]LLM disabled via --no-llm flag.[/yellow]")
    else:
        llm_cfg = get_llm_config()
        llm = create_llm_client(llm_cfg)
        console.print(
            f"[cyan]LLM backend:[/cyan] provider={llm.provider_name} "
            f"model={llm.model} available={llm.available}"
        )

    run_id = str(uuid.uuid4())
    store = SqliteStore(app_cfg.sqlite_path)
    store.insert_run_start(run_id, args.brief)

    initial_state = AgentState(run_id=run_id, brief_id=args.brief, brief=brief)
    final_state = run_agent(initial_state, store=store, llm=llm)
    final_state.completed_at = datetime.now(UTC).isoformat()

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
    if final_state.llm_provenance:
        used_counts = sum(1 for p in final_state.llm_provenance if p.get("used_llm"))
        total = len(final_state.llm_provenance)
        console.print(
            f"LLM calls: {used_counts}/{total} node(s) used the LLM; "
            "see trace for per-node provenance."
        )


if __name__ == "__main__":
    main()
