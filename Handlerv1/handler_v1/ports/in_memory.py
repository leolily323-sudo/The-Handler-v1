"""
In-memory test doubles.
Demonstrates atomic claim + fail-closed persistence semantics.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional, Set

from ..commands.base_command import BaseCommand
from .authorization import AuthorizationPort, AuthorizationDecision, AuthorizationStatus
from .idempotency import (
    IdempotencyPort,
    IdempotencyClaimResult,
    IdempotencyClaimStatus,
    IdempotencyPersistenceError,
    IdempotencyClaimError,
)
from .external_effect import ExternalEffectPort, ExternalOutcome, ExternalStatus


class AlwaysAllowAuthorization(AuthorizationPort):
    def authorize(self, command: BaseCommand) -> AuthorizationDecision:
        return AuthorizationDecision(
            status=AuthorizationStatus.ALLOWED,
            decision_id=f"auth-{command.command_id}",
            reason="test-allow",
        )


class AlwaysDenyAuthorization(AuthorizationPort):
    def authorize(self, command: BaseCommand) -> AuthorizationDecision:
        return AuthorizationDecision(
            status=AuthorizationStatus.DENIED,
            decision_id=f"auth-{command.command_id}",
            reason="test-deny",
        )


class InMemoryIdempotency(IdempotencyPort):
    """
    Process-local, thread-safe claim store.

    Claim failure modes (test injection):
      force_fail_claim_before_own: raise BEFORE recording ownership
        → key remains unclaimed (safe to retry claim later).
      force_fail_claim_after_own: record ownership/block, THEN raise
        → key remains claim-blocking (UNRESOLVED); no second CLAIMED.

    Persistence failure modes:
      force_fail_complete / force_fail_mark_unresolved: raise after
        moving key to unresolved (fail-closed).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._claimed: Dict[str, str] = {}
        self._unresolved: Dict[str, str] = {}
        self._completed: Dict[str, str] = {}
        self.force_fail_complete: Set[str] = set()
        self.force_fail_mark_unresolved: Set[str] = set()
        self.force_fail_claim_before_own: Set[str] = set()
        self.force_fail_claim_after_own: Set[str] = set()

    def claim(self, idempotency_key: str, command_id: str) -> IdempotencyClaimResult:
        with self._lock:
            if idempotency_key in self._completed:
                return IdempotencyClaimResult(
                    status=IdempotencyClaimStatus.ALREADY_COMPLETED,
                    existing_result_reference=self._completed[idempotency_key],
                )
            if idempotency_key in self._unresolved:
                return IdempotencyClaimResult(
                    status=IdempotencyClaimStatus.UNRESOLVED,
                    metadata={"prior_command_id": self._unresolved[idempotency_key]},
                )
            if idempotency_key in self._claimed:
                return IdempotencyClaimResult(status=IdempotencyClaimStatus.IN_PROGRESS)

            if idempotency_key in self.force_fail_claim_before_own:
                self.force_fail_claim_before_own.discard(idempotency_key)
                # Ownership NOT established — safe ambiguous-free failure
                raise IdempotencyClaimError(
                    f"claim failed before ownership for {idempotency_key}"
                )

            # Establish ownership first (atomic under lock)
            self._claimed[idempotency_key] = command_id

            if idempotency_key in self.force_fail_claim_after_own:
                self.force_fail_claim_after_own.discard(idempotency_key)
                # Ownership established then error: fail-closed → unresolved block
                self._unresolved[idempotency_key] = command_id
                self._claimed.pop(idempotency_key, None)
                raise IdempotencyClaimError(
                    f"claim failed after ownership for {idempotency_key}"
                )

            return IdempotencyClaimResult(status=IdempotencyClaimStatus.CLAIMED)

    def mark_unresolved(self, idempotency_key: str, command_id: str) -> None:
        with self._lock:
            if idempotency_key in self.force_fail_mark_unresolved:
                self.force_fail_mark_unresolved.discard(idempotency_key)
                self._unresolved[idempotency_key] = command_id
                self._claimed.pop(idempotency_key, None)
                raise IdempotencyPersistenceError(
                    f"mark_unresolved durable write failed for {idempotency_key}"
                )
            self._unresolved[idempotency_key] = command_id
            self._claimed.pop(idempotency_key, None)

    def complete(self, idempotency_key: str, command_id: str, outcome_reference: str) -> None:
        with self._lock:
            if idempotency_key in self.force_fail_complete:
                self.force_fail_complete.discard(idempotency_key)
                self._unresolved[idempotency_key] = command_id
                self._claimed.pop(idempotency_key, None)
                raise IdempotencyPersistenceError(
                    f"complete durable write failed for {idempotency_key}"
                )
            self._completed[idempotency_key] = outcome_reference
            self._claimed.pop(idempotency_key, None)
            self._unresolved.pop(idempotency_key, None)

    def release(self, idempotency_key: str, command_id: str) -> None:
        with self._lock:
            if self._claimed.get(idempotency_key) == command_id:
                del self._claimed[idempotency_key]


class RecordingEffectPort(ExternalEffectPort):
    def __init__(self, outcome: ExternalOutcome) -> None:
        self.outcome = outcome
        self.calls: list[BaseCommand] = []
        self.raise_on_call: Optional[Exception] = None

    def execute(self, command: BaseCommand) -> ExternalOutcome:
        self.calls.append(command)
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return self.outcome
