"""Structured API errors for consistent client handling."""

from __future__ import annotations


class LegacyShiftError(Exception):
    """Base for errors that map to HTTP responses."""

    def __init__(self, message: str, code: str = "error", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ParseError(LegacyShiftError):
    """Invalid or unparseable source code."""

    def __init__(self, message: str = "Invalid or unparseable Java source."):
        super().__init__(message, code="parse_error", status_code=400)


class PayloadTooLargeError(LegacyShiftError):
    """Request body or source code exceeds size limit."""

    def __init__(self, message: str = "Source code exceeds maximum allowed length."):
        super().__init__(message, code="payload_too_large", status_code=413)


class TimeoutError(LegacyShiftError):
    """Operation exceeded time limit."""

    def __init__(self, message: str = "Migration timed out."):
        super().__init__(message, code="timeout", status_code=408)


class RateLimitExceededError(LegacyShiftError):
    """Too many requests."""

    def __init__(self, message: str = "Rate limit exceeded. Try again later."):
        super().__init__(message, code="rate_limit_exceeded", status_code=429)
