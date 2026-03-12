"""Return the appropriate parser for a given source language."""

from __future__ import annotations

from legacy_shift.parser.ast_parser import JavaParser
from legacy_shift.parser.cobol_parser import CobolParser

SUPPORTED_SOURCE_LANGUAGES = ("java", "cobol")


def get_parser(source_language: str):
    """Return a parser instance for the given source language."""
    lang = (source_language or "java").strip().lower()
    if lang == "cobol":
        return CobolParser()
    if lang == "java":
        return JavaParser()
    raise ValueError(f"Unsupported source language: {source_language}. Use one of: {SUPPORTED_SOURCE_LANGUAGES}")
