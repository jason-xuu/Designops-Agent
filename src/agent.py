from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.nodes.constraint_check import constraint_check_node
from src.nodes.doc_writer import doc_writer_node
from src.nodes.geometry_gen import geometry_gen_node
from src.nodes.planner import planner_node
from src.nodes.risk_assessor import risk_assessor_node
from src.state import AgentState
from src.store.sqlite_store import SqliteStore

NodeFn = Callable[[AgentState], AgentState]


def _wrap(node_name: str, fn: NodeFn, store: SqliteStore | None) -> NodeFn:
    def wrapped(state: AgentState) -> AgentState:
        started = time.perf_counter()
        before = state.model_dump()
        next_state = fn(state)
        duration_ms = int((time.perf_counter() - started) * 1000)
        after = next_state.model_dump()
        next_state.step_traces.append(
            {
                "node": node_name,
                "duration_ms": duration_ms,
                "confidence": next_state.confidence_tags.get(node_name),
                "input_snapshot": {
                    "retry_count": before.get("retry_count", 0),
                    "plan_steps_count": len(before.get("plan_steps", [])),
                    "generated_commands_count": len(before.get("generated_commands", [])),
                },
                "output_snapshot": {
                    "retry_count": after.get("retry_count", 0),
                    "errors_count": len(after.get("errors", [])),
                    "constraint_checks": len(after.get("constraint_results", [])),
                },
            }
        )
        if store:
            store.insert_step(
                run_id=next_state.run_id,
                node=node_name,
                input_data=before,
                output_data=after,
                confidence=next_state.confidence_tags.get(node_name),
                duration_ms=duration_ms,
            )
        return next_state

    return wrapped


def _route_after_constraints(state: AgentState) -> str:
    latest = state.constraint_results[-1] if state.constraint_results else {"is_feasible": False}
    if latest.get("is_feasible", False):
        return "doc_writer"
    if state.retry_count < 2:
        return "geometry_gen"
    return "doc_writer"


def build_agent_graph(store: SqliteStore | None = None):
    graph = StateGraph(AgentState)
    graph.add_node("planner", _wrap("planner", planner_node, store))
    graph.add_node("geometry_gen", _wrap("geometry_gen", geometry_gen_node, store))
    graph.add_node("constraint_check", _wrap("constraint_check", constraint_check_node, store))
    graph.add_node("doc_writer", _wrap("doc_writer", doc_writer_node, store))
    graph.add_node("risk_assessor", _wrap("risk_assessor", risk_assessor_node, store))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "geometry_gen")
    graph.add_edge("geometry_gen", "constraint_check")
    graph.add_conditional_edges(
        "constraint_check",
        _route_after_constraints,
        {"geometry_gen": "geometry_gen", "doc_writer": "doc_writer"},
    )
    graph.add_edge("doc_writer", "risk_assessor")
    graph.add_edge("risk_assessor", END)
    return graph.compile()


def run_agent(initial_state: AgentState, store: SqliteStore | None = None) -> AgentState:
    app = build_agent_graph(store)
    final_state = app.invoke(initial_state)
    if isinstance(final_state, dict):
        return AgentState.model_validate(final_state)
    return final_state
