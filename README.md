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

Three nodes — `planner`, `geometry_gen`, and `risk_assessor` — call a local LLM first and fall back to deterministic implementations on network errors or invalid output. `constraint_check` stays deterministic because zoning math must be repeatable, and `doc_writer` stays deterministic because its job is strictly formatting.

## LLM backend: Ollama (local, free)

The agent uses a local [Ollama](https://ollama.com) instance via its OpenAI-compatible endpoint, matching the setup used in `prompt-reliability-lab` and `nl2geo-rhino-plugin`. No API key, no network egress, no cost.

1. Install Ollama and pull the default model:

   ```bash
   ollama pull llama3.1:8b
   ollama serve  # usually auto-started as a service on macOS
   ```

2. Confirm the daemon is serving:

   ```bash
   curl -s http://localhost:11434/api/tags | jq '.models[].name'
   ```

3. Copy the environment template and adjust if needed:

   ```bash
   cp .env.example .env
   ```

Default settings in `.env.example`:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | Set to `none` to force deterministic fallback. |
| `LLM_MODEL` | `llama3.1:8b` | Any model available to your Ollama daemon. |
| `LLM_TEMPERATURE` | `0.2` | Low temperature for structured JSON. |
| `LLM_MAX_TOKENS` | `1024` | Cap on LLM response size. |
| `LLM_TIMEOUT_S` | `180` | Per-request timeout (cold-start safe). |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible endpoint. |

If Ollama is unreachable or the requested model isn't pulled, the factory transparently swaps in a `NoopLlmClient` so every node uses its deterministic path. The agent never silently errors — fallback reasons are recorded in `state.llm_provenance` and visible in every trace.

## What gets produced

- **Markdown output** for each run in `outputs/`.
- **Full trace JSON** for each run in `traces/`, including per-node `llm_provenance` (used_llm, latency_ms, model, fallback_reason).
- **SQLite audit trail** in `designops_runs.db` with run-level and step-level records.

## Setup

```bash
cd designops-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Keys (if you add any later) only belong in your local `.env`. `.env` and generated runtime artifacts are git-ignored.

## Run

```bash
python run_agent.py --brief residential           # LLM path (Ollama)
python run_agent.py --brief mixed_use             # forced-failure path
python run_agent.py --brief residential --no-llm  # deterministic fallback only
python run_agent.py --brief residential -v        # verbose HTTP/LLM logs
```

Expected result:

- `residential` completes with a feasible path. Typical LLM latency: 30–45s end-to-end on `llama3.1:8b`.
- `mixed_use` triggers the forced infeasibility path and returns fallback alternatives after two retries.

## Test

```bash
pytest tests/ -q
```

25 tests cover:

- Planner logic, tool contracts, and retry behavior (original suite).
- LLM client construction, JSON parsing, retry/error normalization (`test_ollama_client.py`).
- LLM-planner happy path and schema-validation fallback (`test_planner_llm.py`).
- LLM-geometry happy path, unknown-operation fallback, non-numeric-param fallback (`test_geometry_gen_llm.py`).
- Risk assessor LLM narrative and heuristic confidence preservation (`test_risk_assessor_llm.py`).
- LLM config validation, including rejection of unsupported providers (`test_llm_config.py`).

Tests do not hit Ollama — the OpenAI SDK is replaced with a fake in the adapter tests, and node tests inject a `FakeLlmClient`.

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
│   ├── llm/
│   │   ├── client.py           # LlmClient protocol + LlmResponse
│   │   ├── ollama_client.py    # OpenAI-compatible Ollama adapter
│   │   ├── noop_client.py      # offline/CI fallback client
│   │   └── factory.py          # probe-then-select factory
│   ├── nodes/
│   │   ├── planner.py          # LLM-first + deterministic fallback
│   │   ├── geometry_gen.py     # LLM-first + deterministic fallback
│   │   ├── constraint_check.py # deterministic (zoning math)
│   │   ├── doc_writer.py       # deterministic (markdown format)
│   │   ├── risk_assessor.py    # LLM narrative + heuristic confidence
│   │   └── prompts.py          # all LLM system prompts
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
    ├── conftest.py
    ├── _fake_llm.py
    ├── test_planner.py
    ├── test_planner_llm.py
    ├── test_tools.py
    ├── test_retry.py
    ├── test_geometry_gen_llm.py
    ├── test_risk_assessor_llm.py
    ├── test_llm_config.py
    └── test_ollama_client.py
```

## Forced Failure Brief

`brief_mixed_use.json` intentionally sets an infeasible target (`FAR=15` with low height cap) to validate:

- detection of infeasibility,
- retry/fallback path behavior,
- alternative recommendations,
- low-confidence tagging with explicit rationale.

## Notes

- The deterministic tool implementations act as the safety net for every LLM call, so a bad LLM response never breaks a run.
- LLM provenance (used, fallback reason, latency, model) is recorded per node in `state.llm_provenance` and in the per-run trace JSON.

## Milestone Changelog

### v0.1-scaffold
- Established repository structure, dependency metadata, safe local defaults, and two brief fixtures.
- Added onboarding documentation and setup instructions for repeatable local runs.

### v0.2-agent-core
- Implemented the full LangGraph workflow and typed state model.
- Added structured tools, retry/fallback behavior, and SQLite run/step persistence.

### v0.3-tests
- Added targeted test coverage for planner logic, tool outputs, and retry semantics.
- Locked down baseline behavior before external integrations and future expansion.

### v0.4-ollama
- Introduced a local LLM backend via Ollama's OpenAI-compatible endpoint; removed unused `langchain-openai` / `langchain-anthropic` dependencies.
- Added LLM-first paths for planner, geometry generation, and risk assessment, each with a deterministic fallback on probe, network, or schema failure.
- Recorded per-node LLM provenance in state, traces, and SQLite for auditability.
- Expanded the test suite to 25 tests covering the Ollama adapter, node LLM paths, and config validation.
