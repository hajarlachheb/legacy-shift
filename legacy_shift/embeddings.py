"""Optional embedding support for PatternStore (OpenAI). When no API key, store/few-shot are skipped."""

from __future__ import annotations

import logging
from typing import List

from legacy_shift.config import get_settings

logger = logging.getLogger(__name__)

_embedding_model = None


def get_embedding_model():
    """Return an embedding model (OpenAI) if configured, else None."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    settings = get_settings()
    if settings.openai_api_key:
        try:
            from langchain_openai import OpenAIEmbeddings
            _embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
            return _embedding_model
        except Exception as e:
            logger.warning("Could not init OpenAI embeddings: %s", e)
    return None


def get_embedding(text: str) -> List[float] | None:
    """Return embedding vector for text, or None if embeddings not available."""
    model = get_embedding_model()
    if not model:
        return None
    try:
        return model.embed_query(text)
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None
