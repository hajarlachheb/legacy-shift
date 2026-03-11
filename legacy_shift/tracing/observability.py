"""LiteLLM routing + LangSmith / Phoenix observability setup."""

from __future__ import annotations

import logging
import os

from langchain.chat_models import init_chat_model

from legacy_shift.config import get_settings

logger = logging.getLogger(__name__)

_tracing_initialised = False


def init_tracing() -> None:
    """Initialise LangSmith and/or Phoenix tracing (idempotent)."""
    global _tracing_initialised
    if _tracing_initialised:
        return

    settings = get_settings()

    # LangSmith
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
        logger.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)

    # Arize Phoenix
    if settings.phoenix_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor

            endpoint = settings.phoenix_endpoint.rstrip("/") + "/v1/traces"
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(
                SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
            )
            trace.set_tracer_provider(tracer_provider)
            logger.info("Phoenix tracing enabled (endpoint=%s)", endpoint)
        except ImportError:
            logger.warning("Phoenix OTEL dependencies not installed — skipping Phoenix tracing.")

    _tracing_initialised = True


def get_llm(model: str | None = None, temperature: float = 0.0):
    """Return a LangChain chat model routed through LiteLLM.

    Uses `init_chat_model` which automatically delegates to the right
    provider based on the model string (e.g. "gpt-4o", "claude-3-opus",
    "azure/gpt-4o").  LiteLLM environment variables handle auth.
    """
    settings = get_settings()
    model = model or settings.default_model

    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    if settings.anthropic_api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    return init_chat_model(model, temperature=temperature)
