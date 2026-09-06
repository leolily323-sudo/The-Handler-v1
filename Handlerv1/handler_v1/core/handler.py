"""
Handler — controlled execution boundary
Strictly implements Handler Blueprint v1.

Corrections applied:
  First audit  (2026-08-17): UNRESOLVED state, no claim release on effect exception,
                             schema version rejection via injected registry.
  Second audit (2026-08-17):
    - No silent swallowing of idempotency state-management failures (§34).
    - Sanitized exception messages only; raw exception text never enters ExecutionResult.
    - Authorization snapshot/version IDs propagated into result.

Canonical lifecycle (§44) preserved.
Invariants 1–12 remain non-negotiable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Type, Optional
from abc import ABC
import logging

from ..commands.base_command import BaseCommand
from ..results.execution_result import (
    ExecutionResult,
    ResultStatus,
    ErrorCategory,
    ExecutionError,
)
from ..ports.authorization import AuthorizationPort, AuthorizationDecision
from ..ports.idempotency import IdempotencyPort, IdempotencyClaimStatus, IdempotencyPersistenceError, IdempotencyClaimError
from ..ports.external_effect import ExternalEffectPort, ExternalOutcome, ExternalStatus
from ..ports.schema import SchemaRegistryPort

logger = logging.getLogger(__name__)

TCommand = TypeVar("TCommand", bound=BaseCommand)


@dataclass(frozen=True)
class HandlerContext:
    """Injectable infrastructure dependencies. No hidden globals."""
    authorization: AuthorizationPort
    idempotency: IdempotencyPort
    schema_registry: SchemaRegistryPort
    workflow_id: Optional[str] = None
    plan_id: Optional[str] = None


class Handler(ABC, Generic[TCommand]):
    """
    Narrow actuator.
    Executes exactly one declared typed Command.
    Never becomes an orchestrator, policy engine, or capability authority.
    """

    supported_command_type: Type[TCommand]

    def __init__(
        self,
        context: HandlerContext,
        effect_port: ExternalEffectPort[TCommand],
        handler_type: str,
    ) -> None:
        self._ctx = context
        self._effect = effect_port
        self._handler_type = handler_type

    # ── Public entry point ──────────────────────────────────────────────

    def handle(self, command: BaseCommand) -> ExecutionResult:
        """
        Single public method.
        Blueprint §7: handle(Command) → ExecutionResult
        """
        # 1. Validate Command type — exact type identity (Blueprint: only declared type)
        if type(command) is not self.supported_command_type:
            return self._reject(
                command,
                ErrorCategory.VALIDATION_ERROR,
                "Incompatible Command type",
                code="INCOMPATIBLE_COMMAND_TYPE",
            )

        typed_command: TCommand = command  # type: ignore[assignment]

        # 2–3. Structural + identity + schema validation (no side effects)
        try:
            validation_error = self._validate(typed_command)
        except RuntimeError as exc:
            # Schema registry or concrete validator infrastructure failure
            code = str(exc) if str(exc) in {
                "SCHEMA_REGISTRY_INFRASTRUCTURE_FAILURE",
                "VALIDATION_INFRASTRUCTURE_FAILURE",
            } else "VALIDATION_INFRASTRUCTURE_FAILURE"
            return self._internal_error(
                typed_command,
                message="Validation infrastructure failure",
                code=code,
            )
        except Exception:
            logger.exception(
                "Unexpected validation failure for command_id=%s", typed_command.command_id
            )
            return self._internal_error(
                typed_command,
                message="Validation infrastructure failure",
                code="VALIDATION_INFRASTRUCTURE_FAILURE",
            )
        if validation_error is not None:
            return self._reject(
                typed_command,
                ErrorCategory.VALIDATION_ERROR,
                validation_error,
                code="VALIDATION_FAILED",
            )

        # 4. Fresh execution-time authorization (Blueprint §6)
        try:
            decision = self._ctx.authorization.authorize(typed_command)
        except Exception as exc:
            # Sanitize: never put raw exception text into the public result
            logger.exception(
                "Authorization port failure for command_id=%s", typed_command.command_id
            )
            return self._internal_error(
                typed_command,
                message="Authorization infrastructure failure",
                code="AUTHORIZATION_INFRASTRUCTURE_FAILURE",
            )

        if not decision.is_allowed:
            return self._reject(
                typed_command,
                ErrorCategory.NOT_AUTHORIZED,
                decision.reason or "Execution not authorized",
                code="NOT_AUTHORIZED",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
            )

        # 5. Idempotency claim — MUST be atomic (Blueprint §10, §18)
        try:
            claim = self._ctx.idempotency.claim(
                idempotency_key=typed_command.idempotency_key,
                command_id=typed_command.command_id,
            )
        except IdempotencyClaimError:
            # Fail-closed: either ownership was not established, or blocking state was.
            # In both cases no effect may proceed on this call. Do not attempt effect.
            logger.exception(
                "Idempotency claim error for command_id=%s", typed_command.command_id
            )
            return self._internal_error(
                typed_command,
                message="Idempotency claim failed",
                code="IDEMPOTENCY_CLAIM_FAILURE",
            )
        except Exception:
            logger.exception(
                "Idempotency port failure (claim) for command_id=%s", typed_command.command_id
            )
            return self._internal_error(
                typed_command,
                message="Idempotency infrastructure failure",
                code="IDEMPOTENCY_INFRASTRUCTURE_FAILURE",
            )

        if claim.status == IdempotencyClaimStatus.ALREADY_COMPLETED:
            return self._reject(
                typed_command,
                ErrorCategory.IDEMPOTENCY_CONFLICT,
                "Logical operation already completed",
                code="ALREADY_COMPLETED",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
            )
        if claim.status == IdempotencyClaimStatus.UNRESOLVED:
            return self._reject(
                typed_command,
                ErrorCategory.IDEMPOTENCY_CONFLICT,
                "Prior attempt left an unresolved outcome; reconciliation required",
                code="UNRESOLVED_PRIOR_ATTEMPT",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
            )
        if claim.status in (IdempotencyClaimStatus.IN_PROGRESS, IdempotencyClaimStatus.CONFLICT):
            return self._reject(
                typed_command,
                ErrorCategory.IDEMPOTENCY_CONFLICT,
                f"Idempotency conflict: {claim.status.value}",
                code="IDEMPOTENCY_CONFLICT",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
            )
        if not claim.may_proceed:
            return self._reject(
                typed_command,
                ErrorCategory.IDEMPOTENCY_CONFLICT,
                "Unable to claim idempotency identity",
                code="CLAIM_FAILED",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
            )

        # 6. Execute declared operation through the typed effect port
        try:
            outcome = self._effect.execute(typed_command)
        except Exception:
            mark_ok = self._fail_closed_mark_unresolved(
                typed_command.idempotency_key, typed_command.command_id
            )
            logger.exception(
                "External effect exception for command_id=%s (mark_unresolved_ok=%s)",
                typed_command.command_id,
                mark_ok,
            )
            return self._unknown(
                typed_command,
                message="External effect boundary failure; outcome unknown",
                code="EFFECT_BOUNDARY_FAILURE",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
                metadata={"idempotency_mark_unresolved_ok": mark_ok},
            )

        # Validate returned outcome object (fourth-audit Finding 1)
        if not isinstance(outcome, ExternalOutcome):
            mark_ok = self._fail_closed_mark_unresolved(
                typed_command.idempotency_key, typed_command.command_id
            )
            logger.error(
                "Malformed external outcome type=%s for command_id=%s",
                type(outcome).__name__,
                typed_command.command_id,
            )
            return self._unknown(
                typed_command,
                message="Malformed external outcome; outcome unknown",
                code="MALFORMED_EXTERNAL_OUTCOME",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
                metadata={"idempotency_mark_unresolved_ok": mark_ok},
            )
        if not isinstance(getattr(outcome, "status", None), ExternalStatus):
            mark_ok = self._fail_closed_mark_unresolved(
                typed_command.idempotency_key, typed_command.command_id
            )
            logger.error(
                "Malformed external outcome status for command_id=%s",
                typed_command.command_id,
            )
            return self._unknown(
                typed_command,
                message="Malformed external outcome; outcome unknown",
                code="MALFORMED_EXTERNAL_OUTCOME",
                authorization_decision_id=decision.decision_id,
                capability_snapshot_id=decision.capability_snapshot_id,
                policy_snapshot_id=decision.policy_snapshot_id,
                metadata={"idempotency_mark_unresolved_ok": mark_ok},
            )

        # 7. Classify outcome
        result = self._classify(
            typed_command,
            outcome,
            authorization_decision_id=decision.decision_id,
            capability_snapshot_id=decision.capability_snapshot_id,
            policy_snapshot_id=decision.policy_snapshot_id,
        )

        # 8. Terminal state management — fail-closed post-effect contract
        # After the effect boundary, complete()/mark_unresolved() must leave the
        # key in a claim-refusing state. Ports are required to force UNRESOLVED
        # even when the durable write itself fails (see IdempotencyPort docs).
        if result.status in (ResultStatus.SUCCEEDED, ResultStatus.FAILED):
            complete_ok = self._fail_closed_complete(
                typed_command.idempotency_key,
                typed_command.command_id,
                outcome_reference=result.external_reference or result.command_id,
            )
            if not complete_ok:
                logger.error(
                    "Idempotency complete() failed for command_id=%s status=%s "
                    "(port must leave key claim-refusing)",
                    typed_command.command_id,
                    result.status.value,
                )
                # Best-effort force unresolved so claim() refuses even if complete
                # partially failed mid-write. Port is still the authority.
                mark_ok = self._fail_closed_mark_unresolved(
                    typed_command.idempotency_key, typed_command.command_id
                )
                result = ExecutionResult(
                    status=result.status,
                    command_id=result.command_id,
                    idempotency_key=result.idempotency_key,
                    handler_type=result.handler_type,
                    error=result.error,
                    external_reference=result.external_reference,
                    workflow_id=result.workflow_id,
                    plan_id=result.plan_id,
                    authorization_decision_id=result.authorization_decision_id,
                    capability_snapshot_id=result.capability_snapshot_id,
                    policy_snapshot_id=result.policy_snapshot_id,
                    recorded_at=result.recorded_at,
                    metadata={
                        **(result.metadata or {}),
                        "idempotency_complete_ok": False,
                        "idempotency_mark_unresolved_ok": mark_ok,
                        "idempotency_persistence_degraded": True,
                    },
                )
        else:
            mark_ok = self._fail_closed_mark_unresolved(
                typed_command.idempotency_key, typed_command.command_id
            )
            if not mark_ok:
                logger.critical(
                    "Idempotency mark_unresolved() failed AFTER effect for "
                    "command_id=%s — reconciliation required; claim safety "
                    "depends on port fail-closed recovery",
                    typed_command.command_id,
                )
                # External outcome is already UNKNOWN. Surface persistence failure.
                # Do not invent FAILED. Port must still refuse future CLAIMED.
                result = ExecutionResult(
                    status=ResultStatus.UNKNOWN,
                    command_id=result.command_id,
                    idempotency_key=result.idempotency_key,
                    handler_type=result.handler_type,
                    error=ExecutionError(
                        category=ErrorCategory.UNKNOWN_OUTCOME,
                        message="External outcome unknown and idempotency "
                                "persistence failed; reconciliation required",
                        code="IDEMPOTENCY_PERSISTENCE_FAILURE",
                    ),
                    external_reference=result.external_reference,
                    workflow_id=result.workflow_id,
                    plan_id=result.plan_id,
                    authorization_decision_id=result.authorization_decision_id,
                    capability_snapshot_id=result.capability_snapshot_id,
                    policy_snapshot_id=result.policy_snapshot_id,
                    recorded_at=result.recorded_at,
                    metadata={
                        **(result.metadata or {}),
                        "idempotency_mark_unresolved_ok": False,
                        "idempotency_persistence_degraded": True,
                    },
                )

        return result

    # ── Fail-closed idempotency helpers (post-effect) ───────────────────

    def _fail_closed_mark_unresolved(self, idempotency_key: str, command_id: str) -> bool:
        """
        Attempt mark_unresolved after effect boundary.
        Returns True on durable success.
        On IdempotencyPersistenceError / any failure: logs, returns False.
        Port contract requires that even on failure the key remains blocked
        for future claim() (fail-closed).
        """
        try:
            self._ctx.idempotency.mark_unresolved(idempotency_key, command_id)
            return True
        except IdempotencyPersistenceError:
            logger.exception(
                "mark_unresolved persistence failure for key=%s command_id=%s",
                idempotency_key,
                command_id,
            )
            return False
        except Exception:
            logger.exception(
                "mark_unresolved unexpected failure for key=%s command_id=%s",
                idempotency_key,
                command_id,
            )
            return False

    def _fail_closed_complete(
        self, idempotency_key: str, command_id: str, outcome_reference: str
    ) -> bool:
        try:
            self._ctx.idempotency.complete(idempotency_key, command_id, outcome_reference)
            return True
        except IdempotencyPersistenceError:
            logger.exception(
                "complete persistence failure for key=%s command_id=%s",
                idempotency_key,
                command_id,
            )
            return False
        except Exception:
            logger.exception(
                "complete unexpected failure for key=%s command_id=%s",
                idempotency_key,
                command_id,
            )
            return False

    # ── Validation ──────────────────────────────────────────────────────

    def _validate(self, command: TCommand) -> Optional[str]:
        if not command.command_id:
            return "command_id is required"
        if not command.idempotency_key:
            return "idempotency_key is required"
        if not command.schema_version:
            return "schema_version is required"

        command_type = getattr(type(command), "command_type", type(command).__name__)
        try:
            if not self._ctx.schema_registry.is_supported(command_type, command.schema_version):
                return (
                    f"Unsupported schema_version '{command.schema_version}' "
                    f"for command type '{command_type}'"
                )
        except Exception:
            logger.exception("Schema registry failure for command_id=%s", command.command_id)
            # Infrastructure failure — NOT a validation failure of the Command.
            # Raise so handle() can classify as INTERNAL_ERROR.
            raise RuntimeError("SCHEMA_REGISTRY_INFRASTRUCTURE_FAILURE") from None

        try:
            return self._validate_operation(command)
        except Exception:
            logger.exception(
                "Unexpected exception in _validate_operation for command_id=%s",
                command.command_id,
            )
            raise RuntimeError("VALIDATION_INFRASTRUCTURE_FAILURE") from None

    def _validate_operation(self, command: TCommand) -> Optional[str]:
        return None

    # ── Outcome classification ──────────────────────────────────────────

    def _classify(
        self,
        command: TCommand,
        outcome: ExternalOutcome,
        authorization_decision_id: Optional[str],
        capability_snapshot_id: Optional[str] = None,
        policy_snapshot_id: Optional[str] = None,
    ) -> ExecutionResult:
        base_kwargs = dict(
            command_id=command.command_id,
            idempotency_key=command.idempotency_key,
            handler_type=self._handler_type,
            external_reference=outcome.external_reference,
            workflow_id=self._ctx.workflow_id,
            plan_id=self._ctx.plan_id,
            authorization_decision_id=authorization_decision_id,
            capability_snapshot_id=capability_snapshot_id,
            policy_snapshot_id=policy_snapshot_id,
        )

        if outcome.status == ExternalStatus.CONFIRMED_SUCCESS:
            return ExecutionResult(status=ResultStatus.SUCCEEDED, **base_kwargs)

        if outcome.status == ExternalStatus.CONFIRMED_FAILURE:
            # Prefer stable safe message. Integration contract requires
            # outcome.message to already be sanitized; still do not treat it
            # as primary when a stable code is available.
            safe_msg = "External system reported failure"
            if outcome.message and self._is_safe_diagnostic(outcome.message):
                safe_msg = outcome.message
            return ExecutionResult(
                status=ResultStatus.FAILED,
                error=ExecutionError(
                    category=ErrorCategory.EXTERNAL_FAILURE,
                    message=safe_msg,
                    code=self._safe_code(outcome.provider_code, "EXTERNAL_FAILURE"),
                ),
                **base_kwargs,
            )

        if outcome.status == ExternalStatus.REJECTED_BY_PROVIDER:
            safe_msg = "Provider rejected the operation"
            if outcome.message and self._is_safe_diagnostic(outcome.message):
                safe_msg = outcome.message
            return ExecutionResult(
                status=ResultStatus.FAILED,
                error=ExecutionError(
                    category=ErrorCategory.EXTERNAL_FAILURE,
                    message=safe_msg,
                    code=self._safe_code(outcome.provider_code, "PROVIDER_REJECTED"),
                ),
                **base_kwargs,
            )

        if outcome.status == ExternalStatus.TIMEOUT:
            safe_msg = "External operation timed out; outcome unknown"
            if outcome.message and self._is_safe_diagnostic(outcome.message):
                safe_msg = outcome.message
            return ExecutionResult(
                status=ResultStatus.UNKNOWN,
                error=ExecutionError(
                    category=ErrorCategory.TIMEOUT,
                    message=safe_msg,
                    code=self._safe_code(outcome.provider_code, "TIMEOUT"),
                ),
                **base_kwargs,
            )

        if outcome.status == ExternalStatus.AMBIGUOUS:
            safe_msg = "External outcome cannot be determined"
            if outcome.message and self._is_safe_diagnostic(outcome.message):
                safe_msg = outcome.message
            return ExecutionResult(
                status=ResultStatus.UNKNOWN,
                error=ExecutionError(
                    category=ErrorCategory.UNKNOWN_OUTCOME,
                    message=safe_msg,
                    code=self._safe_code(outcome.provider_code, "AMBIGUOUS"),
                ),
                **base_kwargs,
            )

        return ExecutionResult(
            status=ResultStatus.UNKNOWN,
            error=ExecutionError(
                category=ErrorCategory.UNKNOWN_OUTCOME,
                message="Unrecognized external status",
                code="UNRECOGNIZED_EXTERNAL_STATUS",
            ),
            **base_kwargs,
        )


    # ── Safe diagnostic helpers ─────────────────────────────────────────

    @staticmethod
    def _is_safe_diagnostic(text: str) -> bool:
        """
        Conservative heuristic: reject messages that look like they may
        contain secrets. Integration adapters are still the primary sanitizers.
        This is a last-line defense, not the main sanitization boundary.
        """
        if not text or len(text) > 500:
            return False
        lower = text.lower()
        banned = (
            "password", "token=", "secret", "api_key", "apikey", "authorization:",
            "bearer ", "credential", "private_key", "-----begin",
        )
        return not any(b in lower for b in banned)

    @staticmethod
    def _safe_code(provider_code: Optional[str], default: str) -> str:
        if not provider_code:
            return default
        # Codes must be short, printable, non-secret identifiers
        if len(provider_code) > 64 or any(c in provider_code for c in " \n\r\t"):
            return default
        return provider_code

    # ── Result helpers (sanitized messages only) ────────────────────────

    def _reject(
        self,
        command: BaseCommand,
        category: ErrorCategory,
        message: str,
        code: Optional[str] = None,
        authorization_decision_id: Optional[str] = None,
        capability_snapshot_id: Optional[str] = None,
        policy_snapshot_id: Optional[str] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ResultStatus.REJECTED,
            command_id=getattr(command, "command_id", "unknown"),
            idempotency_key=getattr(command, "idempotency_key", None),
            handler_type=self._handler_type,
            error=ExecutionError(category=category, message=message, code=code),
            workflow_id=self._ctx.workflow_id,
            plan_id=self._ctx.plan_id,
            authorization_decision_id=authorization_decision_id,
            capability_snapshot_id=capability_snapshot_id,
            policy_snapshot_id=policy_snapshot_id,
        )

    def _unknown(
        self,
        command: BaseCommand,
        message: str,
        code: Optional[str] = None,
        authorization_decision_id: Optional[str] = None,
        capability_snapshot_id: Optional[str] = None,
        policy_snapshot_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ResultStatus.UNKNOWN,
            command_id=getattr(command, "command_id", "unknown"),
            idempotency_key=getattr(command, "idempotency_key", None),
            handler_type=self._handler_type,
            error=ExecutionError(
                category=ErrorCategory.UNKNOWN_OUTCOME,
                message=message,
                code=code,
            ),
            workflow_id=self._ctx.workflow_id,
            plan_id=self._ctx.plan_id,
            authorization_decision_id=authorization_decision_id,
            capability_snapshot_id=capability_snapshot_id,
            policy_snapshot_id=policy_snapshot_id,
            metadata=metadata,
        )

    def _internal_error(
        self,
        command: BaseCommand,
        message: str,
        code: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ResultStatus.FAILED,
            command_id=getattr(command, "command_id", "unknown"),
            idempotency_key=getattr(command, "idempotency_key", None),
            handler_type=self._handler_type,
            error=ExecutionError(
                category=ErrorCategory.INTERNAL_ERROR,
                message=message,
                code=code,
            ),
            workflow_id=self._ctx.workflow_id,
            plan_id=self._ctx.plan_id,
        )
