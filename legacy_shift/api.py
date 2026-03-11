"""FastAPI server exposing the LegacyShift migration pipeline as REST endpoints.

Run with:
    uvicorn legacy_shift.api:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from legacy_shift.config import get_settings
from legacy_shift.graph.workflow import build_graph
from legacy_shift.parser.ast_parser import JavaParser
from legacy_shift.tracing.observability import init_tracing

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing()
    logger.info("LegacyShift API started")
    yield
    logger.info("LegacyShift API shutting down")


app = FastAPI(
    title="LegacyShift API",
    description="AI-powered legacy code migration — explain, test, and translate safely.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Request / Response models ─────────────────────────────────────────────────


class MigrateRequest(BaseModel):
    source_code: str = Field(..., description="The legacy source code to migrate.")
    source_language: str = Field(default="java", description="Source language (currently 'java').")
    target_language: str = Field(default="python", description="Target language.")
    max_retries: int = Field(default=3, ge=1, le=10, description="Max test-fix iterations.")


class MigrateResponse(BaseModel):
    status: str
    explanation: str
    test_code: str
    translated_code: str
    iterations: int
    test_passed: bool
    test_errors: str


class ExplainRequest(BaseModel):
    source_code: str
    source_language: str = "java"


class ExplainResponse(BaseModel):
    explanation: str
    structure_summary: str


class ParseRequest(BaseModel):
    source_code: str


class ParseResponse(BaseModel):
    summary: str
    package: str | None
    imports: list[str]
    class_count: int
    method_count: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/migrate", response_model=MigrateResponse)
def migrate(req: MigrateRequest) -> MigrateResponse:
    """Run the full migration pipeline (explain → test → translate → verify)."""
    try:
        parser = JavaParser()
        parsed = parser.parse(req.source_code)

        graph = build_graph()
        initial_state = {
            "source_code": req.source_code,
            "source_language": req.source_language,
            "target_language": req.target_language,
            "structure_summary": parsed.summary(),
            "iteration": 0,
            "max_iterations": req.max_retries,
        }

        final = graph.invoke(initial_state)

        return MigrateResponse(
            status=final.get("status", "unknown"),
            explanation=final.get("explanation", ""),
            test_code=final.get("test_code", ""),
            translated_code=final.get("translated_code", ""),
            iterations=final.get("iteration", 0),
            test_passed=final.get("test_passed", False),
            test_errors=final.get("test_errors", ""),
        )
    except Exception as exc:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest) -> ExplainResponse:
    """Explain legacy code in plain English."""
    from legacy_shift.graph.nodes import explain_node

    parser = JavaParser()
    parsed = parser.parse(req.source_code)

    state = {
        "source_code": req.source_code,
        "structure_summary": parsed.summary(),
    }
    result = explain_node(state)

    return ExplainResponse(
        explanation=result["explanation"],
        structure_summary=parsed.summary(),
    )


@app.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    """Parse Java source and return structural summary (no LLM call)."""
    parser = JavaParser()
    parsed = parser.parse(req.source_code)
    return ParseResponse(
        summary=parsed.summary(),
        package=parsed.package,
        imports=parsed.imports,
        class_count=len(parsed.classes),
        method_count=sum(len(c.methods) for c in parsed.classes),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
