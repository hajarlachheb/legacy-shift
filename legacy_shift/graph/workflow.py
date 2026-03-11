"""Assemble the LangGraph migration pipeline with a test-driven feedback loop."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from legacy_shift.feedback.loop import run_tests_node
from legacy_shift.graph.nodes import explain_node, test_gen_node, translate_node
from legacy_shift.graph.state import MigrationState


def _should_retry(state: MigrationState) -> str:
    """Conditional edge: retry translation if tests failed and budget remains."""
    if state.get("test_passed"):
        return "done"
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 3)
    if iteration >= max_iter:
        return "give_up"
    return "retry"


def _mark_partial(state: MigrationState) -> dict:
    return {"status": "partial"}


def build_graph() -> StateGraph:
    """Return a compiled LangGraph that runs the full migration pipeline.

    Pipeline:
        parse (external) → explain → test_gen → translate → run_tests
                                                   ↑              │
                                                   └── retry ─────┘
    """
    graph = StateGraph(MigrationState)

    graph.add_node("explain", explain_node)
    graph.add_node("test_gen", test_gen_node)
    graph.add_node("translate", translate_node)
    graph.add_node("run_tests", run_tests_node)
    graph.add_node("mark_partial", _mark_partial)

    graph.set_entry_point("explain")

    graph.add_edge("explain", "test_gen")
    graph.add_edge("test_gen", "translate")
    graph.add_edge("translate", "run_tests")

    graph.add_conditional_edges(
        "run_tests",
        _should_retry,
        {
            "done": END,
            "retry": "translate",
            "give_up": "mark_partial",
        },
    )

    graph.add_edge("mark_partial", END)

    return graph.compile()
