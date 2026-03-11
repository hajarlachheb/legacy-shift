"""pgvector-backed store for code translation patterns.

Stores known (source_snippet, target_snippet) pairs as embeddings so the
pipeline can retrieve similar past translations and feed them as few-shot
examples to the LLM, improving accuracy over time.
"""

from __future__ import annotations

import logging
from typing import Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from legacy_shift.config import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536


class Base(DeclarativeBase):
    pass


class CodePattern(Base):
    __tablename__ = "code_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_language = Column(String(32), nullable=False)
    target_language = Column(String(32), nullable=False)
    source_snippet = Column(Text, nullable=False)
    target_snippet = Column(Text, nullable=False)
    description = Column(Text, default="")
    embedding = Column(Vector(EMBEDDING_DIM))


class PatternStore:
    """Thin wrapper around a pgvector table of code-translation patterns."""

    def __init__(self, dsn: str | None = None) -> None:
        dsn = dsn or get_settings().postgres_dsn
        self.engine = create_engine(dsn)
        self._session_factory = sessionmaker(bind=self.engine)

    def init_db(self) -> None:
        """Create the table + pgvector extension if they don't exist."""
        with self.engine.connect() as conn:
            conn.execute(select(1))  # verify connectivity
            conn.execute(
                # idempotent
                __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
            )
            conn.commit()
        Base.metadata.create_all(self.engine)
        logger.info("PatternStore database initialised.")

    def add_pattern(
        self,
        source_language: str,
        target_language: str,
        source_snippet: str,
        target_snippet: str,
        embedding: list[float],
        description: str = "",
    ) -> int:
        with self._session_factory() as session:
            pattern = CodePattern(
                source_language=source_language,
                target_language=target_language,
                source_snippet=source_snippet,
                target_snippet=target_snippet,
                description=description,
                embedding=embedding,
            )
            session.add(pattern)
            session.commit()
            return pattern.id  # type: ignore[return-value]

    def search_similar(
        self,
        embedding: list[float],
        source_language: str = "java",
        target_language: str = "python",
        limit: int = 5,
    ) -> Sequence[CodePattern]:
        """Return the closest code patterns by cosine distance."""
        with self._session_factory() as session:
            stmt = (
                select(CodePattern)
                .where(CodePattern.source_language == source_language)
                .where(CodePattern.target_language == target_language)
                .order_by(CodePattern.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            return list(session.scalars(stmt))

    def count(self) -> int:
        with self._session_factory() as session:
            return session.query(CodePattern).count()
