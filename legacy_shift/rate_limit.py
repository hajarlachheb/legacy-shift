"""In-memory rate limiter for /migrate and /explain (optional)."""

from __future__ import annotations

import time
from collections import defaultdict

# (ip, minute_bucket) -> count
_buckets: dict[tuple[str, int], int] = defaultdict(int)
_cleanup_after_seconds = 120


def _minute_bucket() -> int:
    return int(time.time() // 60)


def is_rate_limited(ip: str, limit_per_minute: int) -> bool:
    """Return True if this IP has exceeded the limit this minute."""
    if limit_per_minute <= 0:
        return False
    bucket = _minute_bucket()
    key = (ip, bucket)
    return _buckets[key] >= limit_per_minute


def record_request(ip: str, limit_per_minute: int) -> None:
    """Increment request count for this IP this minute."""
    if limit_per_minute <= 0:
        return
    bucket = _minute_bucket()
    key = (ip, bucket)
    _buckets[key] += 1
    # Simple cleanup: drop old buckets (older than 2 minutes)
    to_del = [k for k in _buckets if bucket - k[1] > 2]
    for k in to_del:
        del _buckets[k]
