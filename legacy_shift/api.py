"""FastAPI server exposing the LegacyShift migration pipeline as REST endpoints.

Run with:
    uvicorn legacy_shift.api:app --reload
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from legacy_shift.config import get_settings
from legacy_shift.errors import LegacyShiftError, ParseError, RateLimitExceededError, TimeoutError
from legacy_shift.rate_limit import is_rate_limited, record_request
from legacy_shift.graph.workflow import build_graph
from legacy_shift.parser.ast_parser import JavaParser
from legacy_shift.tracing.observability import init_tracing

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _cors_origins_list() -> list[str]:
    s = get_settings().cors_origins.strip()
    if not s or s == "*":
        return ["*"]
    return [o.strip() for o in s.split(",") if o.strip()]


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(LegacyShiftError)
def legacy_shift_error_handler(_request: Request, exc: LegacyShiftError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )


# ── Request / Response models ─────────────────────────────────────────────────


def _validate_source_code_length(v: str) -> str:
    max_len = get_settings().max_source_code_chars
    if len(v) > max_len:
        raise ValueError(f"Source code exceeds maximum length ({max_len} characters).")
    return v


class MigrateRequest(BaseModel):
    source_code: str = Field(..., description="The legacy source code to migrate.")
    source_language: str = Field(default="java", description="Source language (currently 'java').")
    target_language: str = Field(default="python", description="Target language.")
    max_retries: int = Field(default=3, ge=1, le=10, description="Max test-fix iterations.")

    @field_validator("source_code")
    @classmethod
    def source_code_length(cls, v: str) -> str:
        return _validate_source_code_length(v)


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

    @field_validator("source_code")
    @classmethod
    def source_code_length(cls, v: str) -> str:
        return _validate_source_code_length(v)


class ExplainResponse(BaseModel):
    explanation: str
    structure_summary: str


class ParseRequest(BaseModel):
    source_code: str

    @field_validator("source_code")
    @classmethod
    def source_code_length(cls, v: str) -> str:
        return _validate_source_code_length(v)


class ParseResponse(BaseModel):
    summary: str
    package: str | None
    imports: list[str]
    class_count: int
    method_count: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


def _run_migrate_sync(req: MigrateRequest) -> MigrateResponse:
    """Synchronous migration (run in thread pool)."""
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


def _run_explain_sync(req: ExplainRequest) -> ExplainResponse:
    """Synchronous explain (run in thread pool)."""
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


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@app.post("/migrate", response_model=MigrateResponse)
async def migrate(request: Request, req: MigrateRequest) -> MigrateResponse:
    """Run the full migration pipeline (explain → test → translate → verify)."""
    settings = get_settings()
    ip = _client_ip(request)
    if is_rate_limited(ip, settings.rate_limit_per_minute):
        raise RateLimitExceededError()
    record_request(ip, settings.rate_limit_per_minute)

    timeout_sec = settings.migration_timeout_seconds
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_migrate_sync, req),
            timeout=timeout_sec,
        )
        return result
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Migration did not complete within {timeout_sec} seconds."
        ) from None
    except ParseError:
        raise
    except Exception as exc:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Store successful translation for future few-shot use (best-effort)
    if result.status == "success" and result.translated_code:
        try:
            from legacy_shift.embeddings import get_embedding
            from legacy_shift.vector.store import PatternStore

            emb = get_embedding(req.source_code[:8000] + "\n" + result.translated_code[:8000])
            if emb:
                store = PatternStore()
                store.init_db()
                store.add_pattern(
                    req.source_language,
                    req.target_language,
                    req.source_code[:50000],
                    result.translated_code[:50000],
                    emb,
                )
                logger.info("Stored translation pattern for future few-shot use")
        except Exception as e:
            logger.warning("Could not store pattern: %s", e)


@app.post("/explain", response_model=ExplainResponse)
async def explain(request: Request, req: ExplainRequest) -> ExplainResponse:
    """Explain legacy code in plain English."""
    settings = get_settings()
    ip = _client_ip(request)
    if is_rate_limited(ip, settings.rate_limit_per_minute):
        raise RateLimitExceededError()
    record_request(ip, settings.rate_limit_per_minute)

    timeout_sec = settings.migration_timeout_seconds
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_explain_sync, req),
            timeout=timeout_sec,
        )
        return result
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Explain did not complete within {timeout_sec} seconds."
        ) from None
    except ParseError:
        raise
    except Exception as exc:
        logger.exception("Explain failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    """Parse Java source and return structural summary (no LLM call)."""
    try:
        parser = JavaParser()
        parsed = parser.parse(req.source_code)
    except ParseError:
        raise
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


@app.get("/")
def root():
    """Serve the web UI."""
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
