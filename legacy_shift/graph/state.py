"""Typed state that flows through the LangGraph migration pipeline."""

from __future__ import annotations

from typing import TypedDict


class MigrationState(TypedDict, total=False):
    # ── Inputs ────────────────────────────────────────────
    source_code: str
    source_language: str
    target_language: str
    structure_summary: str

    # ── Intermediate outputs ──────────────────────────────
    explanation: str
    test_code: str
    translated_code: str

    # ── Feedback loop ─────────────────────────────────────
    test_passed: bool
    test_errors: str
    iteration: int
    max_iterations: int

    # ── Final ─────────────────────────────────────────────
    status: str  # "success" | "partial" | "failed"
