"""Lightweight COBOL parser (regex-based). Produces a structural summary for the LLM.

No tree-sitter dependency. Extracts PROGRAM-ID, paragraphs, and sections.
For full AST parsing, a tree-sitter COBOL grammar could be integrated later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from legacy_shift.errors import ParseError


@dataclass
class CobolParsedCode:
    """Structured representation of a COBOL source file."""

    raw_source: str
    program_id: str | None = None
    paragraphs: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    divisions: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """One-paragraph structural summary suitable for LLM context."""
        parts: list[str] = []
        if self.program_id:
            parts.append(f"Program: {self.program_id}")
        if self.divisions:
            parts.append(f"Divisions: {', '.join(self.divisions)}")
        if self.sections:
            parts.append(f"Sections: {', '.join(self.sections[:20])}" + (" ..." if len(self.sections) > 20 else ""))
        if self.paragraphs:
            parts.append(f"Paragraphs: {', '.join(self.paragraphs[:25])}" + (" ..." if len(self.paragraphs) > 25 else ""))
        if not parts:
            parts.append("COBOL program (structure could not be extracted).")
        return "\n".join(parts)

    @property
    def class_count(self) -> int:
        return 1 if self.program_id else 0

    @property
    def method_count(self) -> int:
        return len(self.paragraphs)


class CobolParser:
    """Extract basic structure from COBOL source via regex (no tree-sitter)."""

    # PROGRAM-ID. name
    _RE_PROGRAM_ID = re.compile(r"PROGRAM-ID\.\s*(\w+)", re.IGNORECASE)
    # Division: IDENTIFICATION, DATA, PROCEDURE, etc.
    _RE_DIVISION = re.compile(r"^\s*(\w+)\s+DIVISION\s*\.", re.IGNORECASE | re.MULTILINE)
    # Section: name SECTION.
    _RE_SECTION = re.compile(r"^\s*(\w+)\s+SECTION\s*\.", re.IGNORECASE | re.MULTILINE)
    # Paragraph: name (word or word-word) at start of line followed by period
    _RE_PARAGRAPH = re.compile(r"^\s{0,7}([\w-]+)\s*\.", re.MULTILINE)

    def parse(self, source: str) -> CobolParsedCode:
        if not source or not source.strip():
            raise ParseError("COBOL source is empty.")
        # Basic COBOL sanity: expect at least IDENTIFICATION or PROGRAM-ID
        if "PROGRAM-ID" not in source.upper() and "IDENTIFICATION" not in source.upper():
            raise ParseError("Source does not look like COBOL (missing PROGRAM-ID or IDENTIFICATION DIVISION).")

        result = CobolParsedCode(raw_source=source)

        m = self._RE_PROGRAM_ID.search(source)
        if m:
            result.program_id = m.group(1)

        result.divisions = list(dict.fromkeys(self._RE_DIVISION.findall(source)))
        result.sections = list(dict.fromkeys(self._RE_SECTION.findall(source)))
        # Paragraphs: exclude reserved words that are often false positives
        reserved = {"MOVE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "IF", "ELSE", "END", "PERFORM", "DISPLAY", "RUN", "STOP"}
        for name in self._RE_PARAGRAPH.findall(source):
            if name.upper() not in reserved and len(name) > 2:
                result.paragraphs.append(name)

        return result
