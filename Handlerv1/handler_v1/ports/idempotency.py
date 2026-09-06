"""
Idempotency Boundary
Blueprint §10, §11, §15, §18, Invariants 4, 10, 11.

Atomic claim + fail-closed persistence after effect boundary.

CLAIM FAILURE CONTRACT (final freeze-candidate):
  claim() is atomic with respect to ownership for a given idempotency key.

  Under concurrency, at most one caller may obtain CLAIMED.

  If claim() raises:
    - Either ownership was NEVER established for this call, OR
    - ownership/claim-blocking state WAS established and remains claim-blocking.
  There is no third state in which claim() fails and a later caller can still
  obtain CLAIMED for the same key in a way that permits a second external effect.

  Adapters MUST implement claim() such that a raised exception cannot leave an
  ambiguous "maybe owned, maybe not, and reclaimable" gap.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Optional, Any
from abc import abstractmethod


class IdempotencyClaimStatus(str, Enum):
    CLAIMED = "CLAIMED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


class IdempotencyPersistenceError(Exception):
    """Raised when the idempotency store cannot durably record post-effect state."""


class IdempotencyClaimError(Exception):
    """
    Raised when claim() cannot complete its atomic protocol.
    After this exception, either:
      (A) this caller did not obtain ownership, and the key is still claimable
          only by a fresh successful claim(); OR
      (B) claim-blocking state was established and remains claim-blocking.
    Implementations MUST NOT leave a reclaimable partial-ownership gap.
    """


@dataclass(frozen=True)
class IdempotencyClaimResult:
    status: IdempotencyClaimStatus
    existing_result_reference: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @property
    def may_proceed(self) -> bool:
        return self.status == IdempotencyClaimStatus.CLAIMED


class IdempotencyPort(Protocol):
    """
    Atomic claim of the logical operation identity.

    Post-effect contract:
      complete() / mark_unresolved() MUST succeed durably or raise
      IdempotencyPersistenceError. On failure, claim() for the key MUST
      remain non-CLAIMED (UNRESOLVED or CONFLICT) — fail-closed.
    """

    @abstractmethod
    def claim(self, idempotency_key: str, command_id: str) -> IdempotencyClaimResult:
        """
        Atomic ownership attempt.
        Returns CLAIMED for exactly one concurrent winner.
        May raise IdempotencyClaimError only under the failure contract above.
        """
        ...

    @abstractmethod
    def mark_unresolved(self, idempotency_key: str, command_id: str) -> None:
        ...

    @abstractmethod
    def complete(self, idempotency_key: str, command_id: str, outcome_reference: str) -> None:
        ...

    @abstractmethod
    def release(self, idempotency_key: str, command_id: str) -> None:
        """Release only when no external effect could have occurred."""
        ...
