# DesignOps Agent

DesignOps Agent is a portfolio project focused on reliable, auditable design workflow automation.  
Given a structured project brief, it produces a planning sequence, generates geometry-oriented commands, checks feasibility against constraints, writes delivery documentation, and records confidence/risk at every step.

## Why this project

This project demonstrates three core capabilities:

- Building a multi-step AI workflow with explicit state transitions.
- Treating reliability and traceability as first-class requirements.
- Designing fallback behavior for infeasible or contradictory briefs.

## Workflow

The execution graph is:

`planner → geometry_gen → constraint_check → doc_writer → risk_assessor`

If constraints fail, the workflow loops through a bounded retry path before continuing with a documented fallback recommendation.

## What gets produced

- **Markdown output** for each run in `outputs/`.
- **Full trace JSON** for each run in `traces/`.
- **SQLite audit trail** in `designops_runs.db` with run-level and step-level records.

## Setup

```bash
cd designops-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set keys only in your local `.env`. Do not commit `.env` or generated runtime artifacts.

## Run

```bash
python run_agent.py --brief residential
python run_agent.py --brief mixed_use
```

Expected result:

- `residential` completes with a feasible path.
- `mixed_use` triggers the forced infeasibility path and returns fallback alternatives.

## Test

```bash
pytest tests/ -v
```

The tests validate planner output, tool contracts, and retry behavior.

## Architecture

```
designops-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── briefs/
│   ├── brief_residential.json
│   └── brief_mixed_use.json
├── src/
│   ├── config.py
│   ├── state.py
│   ├── agent.py
│   ├── nodes/
│   │   ├── planner.py
│   │   ├── geometry_gen.py
│   │   ├── constraint_check.py
│   │   ├── doc_writer.py
│   │   └── risk_assessor.py
│   ├── tools/
│   │   ├── geometry_tool.py
│   │   ├── constraint_tool.py
│   │   └── documentation_tool.py
│   ├── store/
│   │   └── sqlite_store.py
│   └── retry.py
├── traces/
├── outputs/
├── run_agent.py
├── demo_notebook.ipynb
└── tests/
    ├── test_planner.py
    ├── test_tools.py
    └── test_retry.py
```

## Forced Failure Brief

`brief_mixed_use.json` intentionally sets an infeasible target (`FAR=15` with low height cap) to validate:

- detection of infeasibility,
- retry/fallback path behavior,
- alternative recommendations,
- low-confidence tagging with explicit rationale.

## Notes

- The implementation uses deterministic local logic for repeatable behavior and testability.
- LLM provider configuration is scaffolded in `.env.example` and `src/config.py` for future expansion.
