"""
Execution Result Contract
Derived strictly from Handler Blueprint v1 §§8, 9, 13, 30, 44.

Four mandatory statuses:
  SUCCEEDED | FAILED | REJECTED | UNKNOWN

Error categories are explicit and must not be collapsed.
Corrected per second ChatGPT audit (2026-08-17):
  - Result object enforces basic status/error invariants.
  - Authorization snapshot/version fields preserved for observability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime, timezone


class ResultStatus(str, Enum):
    """Blueprint §8 — mandatory four-valued outcome model."""
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class ErrorCategory(str, Enum):
    """Blueprint §9 + §13 — meaningful failure categories."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    EXTERNAL_FAILURE = "EXTERNAL_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class ExecutionError:
    """
    Typed error payload.
    Sensitive provider / infrastructure details must not leak into the public result.
    """
    category: ErrorCategory
    message: str
    # Safe, non-sensitive diagnostic code (never raw provider secrets or exception text)
    code: Optional[str] = None
    details: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ExecutionResult:
    """
    Strongly typed execution outcome.
    Blueprint §8, §17, §19, §20, §30.
    """
    status: ResultStatus
    command_id: str
    idempotency_key: Optional[str] = None
    handler_type: Optional[str] = None
    error: Optional[ExecutionError] = None
    external_reference: Optional[str] = None
    # Correlation / observability fields (Blueprint §19, §20)
    workflow_id: Optional[str] = None
    plan_id: Optional[str] = None
    authorization_decision_id: Optional[str] = None
    capability_snapshot_id: Optional[str] = None
    policy_snapshot_id: Optional[str] = None
    # Wall-clock is infrastructure concern only; not used for authorization
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Opaque safe metadata for Event/State infrastructure
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        # Enforce basic semantic invariants (ChatGPT Finding 4 recommendation)
        if self.status == ResultStatus.SUCCEEDED and self.error is not None:
            raise ValueError("SUCCEEDED result must not carry an error")
        if self.status in (ResultStatus.FAILED, ResultStatus.REJECTED, ResultStatus.UNKNOWN):
            if self.error is None:
                raise ValueError(f"{self.status.value} result must carry an ExecutionError")

    def is_terminal_success(self) -> bool:
        return self.status == ResultStatus.SUCCEEDED

    def is_rejected(self) -> bool:
        return self.status == ResultStatus.REJECTED

    def is_unknown(self) -> bool:
        return self.status == ResultStatus.UNKNOWN

    def is_failed(self) -> bool:
        return self.status == ResultStatus.FAILED
