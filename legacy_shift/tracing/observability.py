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
    """Return a LangChain chat model.

    Priority: Azure OpenAI (if configured) → OpenAI/Anthropic (if keys set) → Ollama (free, local).
    """
    settings = get_settings()

    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            azure_deployment=settings.azure_openai_deployment_id or settings.default_model,
            api_version=settings.azure_openai_api_version,
            temperature=temperature,
        )

    model = model or settings.default_model

    # Free path: use Ollama (local, no API key) when model is ollama/* or no paid keys set
    use_ollama = model.lower().startswith("ollama/") or (
        not settings.openai_api_key
        and not settings.anthropic_api_key
        and (not model or model == "gpt-4o")
    )
    if use_ollama:
        if model.lower().startswith("ollama/"):
            ollama_model = model.split("/", 1)[1].strip() or "llama3.2"
        else:
            ollama_model = "llama3.2"
        logger.info("Using free local model: ollama/%s (Ollama at %s)", ollama_model, settings.ollama_base_url)
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )

    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    if settings.anthropic_api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    return init_chat_model(model, temperature=temperature)
