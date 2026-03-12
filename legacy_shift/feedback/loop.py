"""Feedback loop: write translated code + tests to a temp dir, run pytest, capture results."""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from legacy_shift.graph.state import MigrationState

logger = logging.getLogger(__name__)


def run_tests_node(state: MigrationState) -> dict:
    """Execute the generated tests against the translated code.

    Writes `translated.py` and `test_translated.py` into a temporary
    directory, runs pytest, and reports pass/fail + error output.
    """
    translated_code = state.get("translated_code", "")
    test_code = state.get("test_code", "")

    if not translated_code or not test_code:
        return {
            "test_passed": False,
            "test_errors": "Missing translated code or test code.",
            "status": "failed",
        }

    with tempfile.TemporaryDirectory(prefix="legacyshift_") as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "translated.py").write_text(translated_code, encoding="utf-8")
        (tmp / "test_translated.py").write_text(test_code, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_translated.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=60,
        )

        passed = result.returncode == 0
        output = result.stdout + "\n" + result.stderr

        if passed:
            logger.info("All tests passed on iteration %d", state.get("iteration", 0))
            return {
                "test_passed": True,
                "test_errors": "",
                "status": "success",
            }

        # Keep last 80 lines so the LLM sees the first failure and stack trace
        error_lines = output.strip().split("\n")
        truncated = "\n".join(error_lines[-80:]) if len(error_lines) > 80 else output
        if len(truncated) > 4000:
            truncated = truncated[-4000:]
        logger.warning(
            "Tests failed on iteration %d:\n%s",
            state.get("iteration", 0),
            truncated[-1500:],
        )
        return {
            "test_passed": False,
            "test_errors": truncated,
        }
