"""LangGraph node functions — each takes MigrationState and returns a partial update."""

from __future__ import annotations

import logging
import re

from legacy_shift.graph.state import MigrationState
from legacy_shift.prompts import EXPLAIN_PROMPT, TEST_GEN_PROMPT, TRANSLATE_PROMPT
from legacy_shift.prompts.translate import TRANSLATE_FEEDBACK_SECTION
from legacy_shift.tracing.observability import get_llm

logger = logging.getLogger(__name__)


def _extract_code_block(text: str) -> str:
    """Pull the first fenced code block out of an LLM response."""
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


# ── Node 1: Explain ──────────────────────────────────────────────────────────

def explain_node(state: MigrationState) -> dict:
    """Ask the LLM to explain the legacy source code in plain English."""
    llm = get_llm()
    chain = EXPLAIN_PROMPT | llm
    result = chain.invoke(
        {
            "source_code": state["source_code"],
            "structure_summary": state.get("structure_summary", ""),
        }
    )
    explanation = result.content if hasattr(result, "content") else str(result)
    logger.info("Explanation generated (%d chars)", len(explanation))
    return {"explanation": explanation}


# ── Node 2: Generate Tests ───────────────────────────────────────────────────

def test_gen_node(state: MigrationState) -> dict:
    """Generate a pytest suite that will verify the translated code."""
    llm = get_llm()
    chain = TEST_GEN_PROMPT | llm
    result = chain.invoke(
        {
            "source_code": state["source_code"],
            "explanation": state["explanation"],
            "structure_summary": state.get("structure_summary", ""),
        }
    )
    raw = result.content if hasattr(result, "content") else str(result)
    test_code = _extract_code_block(raw)
    logger.info("Test suite generated (%d chars)", len(test_code))
    return {"test_code": test_code}


# ── Node 3: Translate ────────────────────────────────────────────────────────

def translate_node(state: MigrationState) -> dict:
    """Translate the legacy code into the target language."""
    llm = get_llm()
    chain = TRANSLATE_PROMPT | llm

    iteration = state.get("iteration", 0)
    feedback_section = ""
    if iteration > 0 and state.get("test_errors"):
        feedback_section = TRANSLATE_FEEDBACK_SECTION.format(
            previous_translation=state.get("translated_code", ""),
            test_errors=state["test_errors"],
        )

    result = chain.invoke(
        {
            "source_code": state["source_code"],
            "explanation": state["explanation"],
            "structure_summary": state.get("structure_summary", ""),
            "feedback_section": feedback_section,
        }
    )
    raw = result.content if hasattr(result, "content") else str(result)
    translated_code = _extract_code_block(raw)
    logger.info("Translation generated (iteration %d, %d chars)", iteration, len(translated_code))
    return {"translated_code": translated_code, "iteration": iteration + 1}
