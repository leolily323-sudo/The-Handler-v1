"""Handler Result Contract — Blueprint §8, §9, §13, §30."""

from .execution_result import (
    ExecutionResult,
    ResultStatus,
    ErrorCategory,
    ExecutionError,
)

__all__ = [
    "ExecutionResult",
    "ResultStatus",
    "ErrorCategory",
    "ExecutionError",
]
