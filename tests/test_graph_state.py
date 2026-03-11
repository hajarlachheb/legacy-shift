"""Tests for the LangGraph state definition and workflow structure."""

from legacy_shift.graph.state import MigrationState
from legacy_shift.graph.workflow import build_graph


def test_migration_state_accepts_all_fields():
    state: MigrationState = {
        "source_code": "class Foo {}",
        "source_language": "java",
        "target_language": "python",
        "structure_summary": "Class Foo with no methods",
        "explanation": "A trivial class.",
        "test_code": "def test_foo(): pass",
        "translated_code": "class Foo: pass",
        "test_passed": True,
        "test_errors": "",
        "iteration": 1,
        "max_iterations": 3,
        "status": "success",
    }
    assert state["status"] == "success"


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_graph_has_expected_nodes():
    """The compiled graph should contain our named nodes."""
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    for expected in ("explain", "test_gen", "translate", "run_tests"):
        assert expected in node_names, f"Missing node: {expected}"
