"""
Unified API response envelope.

Frontend contract (non-negotiable):
  Success: { "status": "success", "data": <payload> }
  Error:   { "status": "error",   "detail": "..." }

The frontend Axios client destructures every response as `response.data.data`.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Unified response envelope for all Cadencia API endpoints.

    The frontend destructures `response.data.data` — this envelope must be:
        { "status": "success", "data": <T> }
    """

    status: str = "success"
    data: T | None = None

    model_config = {"arbitrary_types_allowed": True}


class ApiErrorResponse(BaseModel):
    """
    Error response envelope.

    The frontend expects:
        { "status": "error", "detail": "Human-readable message" }
    """

    status: str = "error"
    detail: str


# ── Typed error response helpers ───────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Structured error detail included in error_response()."""

    code: str
    message: str
    field: Optional[str] = None


class ResponseMeta(BaseModel):
    """Metadata included in typed error responses."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TypedErrorResponse(BaseModel):
    """
    Typed error response returned by error_response().

    Shape:
        { "success": false, "data": null, "error": { code, message, field }, "meta": { request_id } }
    """

    success: bool = False
    data: None = None
    error: ErrorDetail
    meta: ResponseMeta


def success_response(data: T) -> dict[str, Any]:
    """Factory for successful responses — returns a plain dict envelope."""
    return {"status": "success", "data": data}


def error_dict(detail: str) -> dict[str, Any]:
    """Return the canonical error envelope as a plain dict (for JSONResponse)."""
    return {"status": "error", "detail": detail}


def error_response(
    code: str,
    message: str,
    request_id: uuid.UUID | None = None,
    field: str | None = None,
) -> TypedErrorResponse:
    """
    Factory for typed error responses used by error handlers and tests.

    Returns a TypedErrorResponse with success=False, structured ErrorDetail,
    and ResponseMeta containing the request_id for correlation.
    """
    return TypedErrorResponse(
        error=ErrorDetail(code=code, message=message, field=field),
        meta=ResponseMeta(
            request_id=str(request_id) if request_id else str(uuid.uuid4())
        ),
    )
