"""
External Effect Boundary
Blueprint §12, §28, Invariant 8.

All external side effects occur only through this typed port.
Handler core logic stays decoupled from provider transport details.

Corrected per third ChatGPT audit (2026-08-17):
  ExternalOutcome.message and provider_code are formally required to be
  safe for downstream logging. Integration adapters MUST sanitize before
  constructing ExternalOutcome. Handler treats these fields as already safe
  but never trusts them as authorization or secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Optional, Any, Generic, TypeVar
from abc import abstractmethod

from ..commands.base_command import BaseCommand


class ExternalStatus(str, Enum):
    """Outcome reported by the external system / gateway."""
    CONFIRMED_SUCCESS = "CONFIRMED_SUCCESS"
    CONFIRMED_FAILURE = "CONFIRMED_FAILURE"
    TIMEOUT = "TIMEOUT"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED_BY_PROVIDER = "REJECTED_BY_PROVIDER"


@dataclass(frozen=True)
class ExternalOutcome:
    """
    Structured outcome from the integration port.

    CONTRACT: `message` and `provider_code` MUST be safe for downstream
    logging and observability. They MUST NOT contain credentials, tokens,
    raw provider response bodies, secrets, or private identifiers.
    Integration adapters are responsible for sanitization before constructing
    this object. Handler will not re-sanitize, but will prefer stable codes.
    """
    status: ExternalStatus
    external_reference: Optional[str] = None
    # Safe diagnostic code only (never secrets)
    provider_code: Optional[str] = None
    # Safe, non-sensitive diagnostic message only
    message: Optional[str] = None
    raw_safe_metadata: Optional[dict[str, Any]] = None


TCommand = TypeVar("TCommand", bound=BaseCommand)


class ExternalEffectPort(Protocol, Generic[TCommand]):
    """
    Typed gateway for one specific Command type.
    Concrete implementations live outside the Handler core.
    """

    @abstractmethod
    def execute(self, command: TCommand) -> ExternalOutcome:
        """
        Perform the external side effect.
        Must return an honest classification of what is known.
        message/provider_code MUST already be sanitized.
        """
        ...
