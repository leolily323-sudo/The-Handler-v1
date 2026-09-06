"""
Execution-Time Authorization Boundary
Blueprint §6, §22, §23, Invariant 3.

Authorization is injected. Handler NEVER manufactures, weakens,
overrides, or reinterprets authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Optional, Any
from abc import abstractmethod

from ..commands.base_command import BaseCommand


class AuthorizationStatus(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"


@dataclass(frozen=True)
class AuthorizationDecision:
    """Non-durable decision produced by the authorization boundary."""
    status: AuthorizationStatus
    decision_id: Optional[str] = None
    reason: Optional[str] = None
    # Snapshot / version information for audit (Blueprint §19)
    capability_snapshot_id: Optional[str] = None
    policy_snapshot_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @property
    def is_allowed(self) -> bool:
        return self.status == AuthorizationStatus.ALLOWED


class AuthorizationPort(Protocol):
    """
    Injected port. Handler calls this immediately before effect.
    The Handler itself contains zero authorization logic.
    """

    @abstractmethod
    def authorize(self, command: BaseCommand) -> AuthorizationDecision:
        """Fresh execution-time authorization decision."""
        ...
