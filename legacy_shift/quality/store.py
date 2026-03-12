"""SQLite-backed store for migration run outcomes (quality tracking)."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


def quality_score(status: str, iterations: int, test_passed: bool) -> float:
    """Simple quality score in [0, 1]. Success=1, partial=0.5, failed=0; discount by iterations."""
    if status == "success" and test_passed:
        # 1.0 for success in 1 iter, slightly less for more iters
        return max(0.5, 1.0 - (iterations - 1) * 0.05)
    if status == "partial":
        return max(0.2, 0.5 - iterations * 0.05)
    return 0.0


class MigrationRunStore:
    """Persist migration outcomes to SQLite for stats and history."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path(__file__).resolve().parent.parent.parent / "data" / "migration_runs.db"
        if db_path != ":memory:":
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = None
        self._db_path_str = str(db_path)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path_str, timeout=10.0)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS migration_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_utc TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    status TEXT NOT NULL,
                    test_passed INTEGER NOT NULL,
                    iterations INTEGER NOT NULL,
                    duration_ms INTEGER,
                    source_len INTEGER,
                    quality_score REAL,
                    UNIQUE(id)
                )
                """
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_created ON migration_runs(created_at_utc)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_status ON migration_runs(status)"
            )

    def record(
        self,
        source_language: str,
        target_language: str,
        status: str,
        test_passed: bool,
        iterations: int,
        duration_ms: int | None = None,
        source_len: int | None = None,
    ) -> int:
        """Record one migration run. Returns row id."""
        from datetime import datetime, timezone

        score = quality_score(status, iterations, test_passed)
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO migration_runs
                (created_at_utc, source_language, target_language, status, test_passed, iterations, duration_ms, source_len, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (now, source_language, target_language, status, 1 if test_passed else 0, iterations, duration_ms, source_len, score),
            )
            return c.lastrowid or 0

    def get_stats(self, limit_days: int | None = 30) -> dict:
        """Return aggregate stats (success rate, avg iterations, total runs, recent quality)."""
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            if limit_days:
                c.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN status = 'success' AND test_passed THEN 1 ELSE 0 END) as success_count,
                           AVG(iterations) as avg_iterations,
                           AVG(quality_score) as avg_quality
                    FROM migration_runs
                    WHERE created_at_utc >= datetime('now', ? || ' days')
                    """,
                    (f"-{limit_days}",),
                )
            else:
                c.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN status = 'success' AND test_passed THEN 1 ELSE 0 END) as success_count,
                           AVG(iterations) as avg_iterations,
                           AVG(quality_score) as avg_quality
                    FROM migration_runs
                    """
                )
            row = c.fetchone()
        if not row or row["total"] == 0:
            return {
                "total_runs": 0,
                "success_count": 0,
                "success_rate": 0.0,
                "avg_iterations": 0.0,
                "avg_quality_score": 0.0,
            }
        total = row["total"]
        success = row["success_count"] or 0
        return {
            "total_runs": total,
            "success_count": success,
            "success_rate": round(success / total, 4),
            "avg_iterations": round(row["avg_iterations"] or 0, 2),
            "avg_quality_score": round(row["avg_quality"] or 0.0, 4),
        }

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Return recent migration runs (newest first)."""
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            c.execute(
                """
                SELECT id, created_at_utc, source_language, target_language, status, test_passed, iterations, duration_ms, quality_score
                FROM migration_runs
                ORDER BY created_at_utc DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = c.fetchall()
        return [
            {
                "id": r["id"],
                "created_at_utc": r["created_at_utc"],
                "source_language": r["source_language"],
                "target_language": r["target_language"],
                "status": r["status"],
                "test_passed": bool(r["test_passed"]),
                "iterations": r["iterations"],
                "duration_ms": r["duration_ms"],
                "quality_score": round(r["quality_score"], 4) if r["quality_score"] is not None else None,
            }
            for r in rows
        ]
