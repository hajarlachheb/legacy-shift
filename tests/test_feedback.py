"""Tests for the feedback loop — verifies that test execution works correctly."""

from legacy_shift.feedback.loop import run_tests_node


def test_run_tests_with_passing_code():
    """When translated code and tests are valid, run_tests_node should pass."""
    state = {
        "translated_code": "def add(a, b):\n    return a + b\n",
        "test_code": (
            "from translated import add\n\n"
            "def test_add_positive():\n"
            "    assert add(2, 3) == 5\n\n"
            "def test_add_negative():\n"
            "    assert add(-1, -2) == -3\n"
        ),
        "iteration": 1,
    }
    result = run_tests_node(state)
    assert result["test_passed"] is True
    assert result["status"] == "success"


def test_run_tests_with_failing_code():
    """When tests fail, run_tests_node should report failure."""
    state = {
        "translated_code": "def add(a, b):\n    return a - b  # bug!\n",
        "test_code": (
            "from translated import add\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
        ),
        "iteration": 1,
    }
    result = run_tests_node(state)
    assert result["test_passed"] is False
    assert result["test_errors"] != ""


def test_run_tests_with_missing_code():
    """When translated code is empty, run_tests_node should handle gracefully."""
    state = {
        "translated_code": "",
        "test_code": "def test_noop(): pass",
        "iteration": 0,
    }
    result = run_tests_node(state)
    assert result["test_passed"] is False
    assert "Missing" in result["test_errors"]
