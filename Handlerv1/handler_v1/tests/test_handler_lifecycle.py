"""
Handler v1 — Lifecycle & Acceptance Tests
Covers Blueprint §40 Acceptance Criteria + ChatGPT audit regression cases.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

from handler_v1.commands.example_commands import SendNotificationCommand
from handler_v1.core.handler import HandlerContext
from handler_v1.core.notification_handler import SendNotificationHandler
from handler_v1.ports.in_memory import (
    AlwaysAllowAuthorization,
    AlwaysDenyAuthorization,
    InMemoryIdempotency,
    RecordingEffectPort,
)
from handler_v1.ports.schema import StaticSchemaRegistry
from handler_v1.ports.external_effect import ExternalOutcome, ExternalStatus
from handler_v1.results.execution_result import ResultStatus, ErrorCategory


def _make_command(
    command_id: str = "cmd-001",
    idempotency_key: str = "idem-001",
    recipient: str = "user@example.com",
    channel: str = "email",
    body: str = "hello",
    schema_version: str = "1.0",
) -> SendNotificationCommand:
    return SendNotificationCommand(
        command_id=command_id,
        idempotency_key=idempotency_key,
        schema_version=schema_version,
        recipient=recipient,
        channel=channel,
        body=body,
    )


def _handler(
    auth=None,
    idem=None,
    outcome: ExternalOutcome | None = None,
    schema_registry=None,
) -> tuple[SendNotificationHandler, RecordingEffectPort, InMemoryIdempotency]:
    auth = auth or AlwaysAllowAuthorization()
    idem = idem or InMemoryIdempotency()
    schema_registry = schema_registry or StaticSchemaRegistry()
    outcome = outcome or ExternalOutcome(
        status=ExternalStatus.CONFIRMED_SUCCESS,
        external_reference="ext-123",
    )
    port = RecordingEffectPort(outcome)
    ctx = HandlerContext(
        authorization=auth,
        idempotency=idem,
        schema_registry=schema_registry,
    )
    h = SendNotificationHandler(context=ctx, effect_port=port)
    return h, port, idem


# ── Success path ───────────────────────────────────────────────────────

def test_successful_execution():
    h, port, _ = _handler()
    cmd = _make_command()
    result = h.handle(cmd)

    assert result.status == ResultStatus.SUCCEEDED
    assert result.command_id == "cmd-001"
    assert result.idempotency_key == "idem-001"
    assert result.external_reference == "ext-123"
    assert result.handler_type == "SendNotificationHandler"
    assert len(port.calls) == 1
    assert port.calls[0] is cmd


# ── Rejection paths (no external effect) ────────────────────────────────

def test_incompatible_command_type_rejected():
    class OtherCommand:
        command_id = "x"
        idempotency_key = "y"
        schema_version = "1"

    h, port, _ = _handler()
    result = h.handle(OtherCommand())  # type: ignore

    assert result.status == ResultStatus.REJECTED
    assert result.error.category == ErrorCategory.VALIDATION_ERROR
    assert len(port.calls) == 0


def test_authorization_denied_no_effect():
    h, port, _ = _handler(auth=AlwaysDenyAuthorization())
    result = h.handle(_make_command())

    assert result.status == ResultStatus.REJECTED
    assert result.error.category == ErrorCategory.NOT_AUTHORIZED
    assert len(port.calls) == 0


def test_invalid_channel_rejected():
    h, port, _ = _handler()
    cmd = _make_command(channel="carrier-pigeon")
    result = h.handle(cmd)

    assert result.status == ResultStatus.REJECTED
    assert result.error.category == ErrorCategory.VALIDATION_ERROR
    assert "unsupported channel" in result.error.message
    assert len(port.calls) == 0


def test_missing_recipient_rejected():
    h, port, _ = _handler()
    cmd = _make_command(recipient="   ")
    result = h.handle(cmd)

    assert result.status == ResultStatus.REJECTED
    assert result.error.category == ErrorCategory.VALIDATION_ERROR
    assert len(port.calls) == 0


def test_unsupported_schema_version_rejected():
    """ChatGPT Finding 3 — unsupported schema versions must be rejected."""
    h, port, _ = _handler()
    cmd = _make_command(schema_version="999.999")
    result = h.handle(cmd)

    assert result.status == ResultStatus.REJECTED
    assert result.error.category == ErrorCategory.VALIDATION_ERROR
    assert "Unsupported schema_version" in result.error.message
    assert len(port.calls) == 0


# ── Idempotency ────────────────────────────────────────────────────────

def test_duplicate_command_rejected_after_completion():
    idem = InMemoryIdempotency()
    h, port, _ = _handler(idem=idem)
    cmd = _make_command()

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.SUCCEEDED
    assert len(port.calls) == 1

    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1


def test_concurrent_duplicate_claim_is_safe():
    idem = InMemoryIdempotency()
    success_outcome = ExternalOutcome(
        status=ExternalStatus.CONFIRMED_SUCCESS,
        external_reference="ext-race",
    )
    port = RecordingEffectPort(success_outcome)
    ctx = HandlerContext(
        authorization=AlwaysAllowAuthorization(),
        idempotency=idem,
        schema_registry=StaticSchemaRegistry(),
    )
    h = SendNotificationHandler(context=ctx, effect_port=port)

    cmd = _make_command(command_id="race-cmd", idempotency_key="race-key")

    def worker():
        return h.handle(cmd)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker) for _ in range(8)]
        results = [f.result() for f in as_completed(futures)]

    succeeded = [r for r in results if r.status == ResultStatus.SUCCEEDED]
    rejected = [r for r in results if r.status == ResultStatus.REJECTED]

    assert len(succeeded) == 1
    assert len(rejected) == 7
    assert all(r.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT for r in rejected)
    assert len(port.calls) == 1


# ── External outcome classification ─────────────────────────────────────

def test_confirmed_failure_is_failed():
    outcome = ExternalOutcome(
        status=ExternalStatus.CONFIRMED_FAILURE,
        message="provider rejected",
        provider_code="P-ERR",
    )
    h, port, _ = _handler(outcome=outcome)
    result = h.handle(_make_command())

    assert result.status == ResultStatus.FAILED
    assert result.error.category == ErrorCategory.EXTERNAL_FAILURE
    assert len(port.calls) == 1


def test_timeout_is_unknown_not_failed():
    outcome = ExternalOutcome(status=ExternalStatus.TIMEOUT, message="timed out")
    h, port, _ = _handler(outcome=outcome)
    result = h.handle(_make_command())

    assert result.status == ResultStatus.UNKNOWN
    assert result.error.category == ErrorCategory.TIMEOUT
    assert len(port.calls) == 1


def test_ambiguous_is_unknown():
    outcome = ExternalOutcome(status=ExternalStatus.AMBIGUOUS, message="network partition")
    h, port, _ = _handler(outcome=outcome)
    result = h.handle(_make_command())

    assert result.status == ResultStatus.UNKNOWN
    assert result.error.category == ErrorCategory.UNKNOWN_OUTCOME


# ── ChatGPT Finding 1 regression: retry after UNKNOWN must not re-execute ─

def test_retry_after_unknown_does_not_duplicate_effect():
    """
    CRITICAL regression for Finding 1.
    First call → TIMEOUT → UNKNOWN (claim becomes unresolved).
    Second call with same key/id → REJECTED (IDEMPOTENCY_CONFLICT).
    External effect must occur exactly once.
    """
    idem = InMemoryIdempotency()
    timeout_outcome = ExternalOutcome(status=ExternalStatus.TIMEOUT, message="timed out")
    h, port, _ = _handler(idem=idem, outcome=timeout_outcome)

    cmd = _make_command(command_id="cmd-unk", idempotency_key="idem-unk")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.UNKNOWN
    assert len(port.calls) == 1

    # Second attempt must NOT re-execute
    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert "unresolved" in r2.error.message.lower()
    assert len(port.calls) == 1  # still only one external call


# ── ChatGPT Finding 2 regression: effect exception must not release claim ─

def test_effect_exception_preserves_unresolved_claim():
    """
    CRITICAL regression for Finding 2.
    effect.execute() raises → UNKNOWN.
    Claim must remain unresolved so a subsequent call cannot re-execute.
    """
    idem = InMemoryIdempotency()
    port = RecordingEffectPort(
        ExternalOutcome(status=ExternalStatus.CONFIRMED_SUCCESS, external_reference="x")
    )
    port.raise_on_call = RuntimeError("transport failure after possible accept")

    ctx = HandlerContext(
        authorization=AlwaysAllowAuthorization(),
        idempotency=idem,
        schema_registry=StaticSchemaRegistry(),
    )
    h = SendNotificationHandler(context=ctx, effect_port=port)
    cmd = _make_command(command_id="cmd-exc", idempotency_key="idem-exc")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.UNKNOWN
    assert len(port.calls) == 1

    # Disable the exception so we can observe whether a second effect would occur
    port.raise_on_call = None
    port.outcome = ExternalOutcome(
        status=ExternalStatus.CONFIRMED_SUCCESS, external_reference="should-not-happen"
    )

    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1  # no second external call


# ── Internal exception coverage ─────────────────────────────────────────

def test_authorization_port_exception_is_internal_error():
    class BoomAuth(AlwaysAllowAuthorization):
        def authorize(self, command):
            raise RuntimeError("auth infrastructure down")

    h, port, _ = _handler(auth=BoomAuth())
    result = h.handle(_make_command())

    assert result.status == ResultStatus.FAILED
    assert result.error.category == ErrorCategory.INTERNAL_ERROR
    assert len(port.calls) == 0


def test_idempotency_port_exception_is_internal_error():
    class BoomIdem(InMemoryIdempotency):
        def claim(self, idempotency_key, command_id):
            raise RuntimeError("idem store unavailable")

    h, port, _ = _handler(idem=BoomIdem())
    result = h.handle(_make_command())

    assert result.status == ResultStatus.FAILED
    assert result.error.category == ErrorCategory.INTERNAL_ERROR
    assert len(port.calls) == 0


# ── Correlation preservation ────────────────────────────────────────────

def test_correlation_fields_propagated():
    auth = AlwaysAllowAuthorization()
    idem = InMemoryIdempotency()
    port = RecordingEffectPort(
        ExternalOutcome(status=ExternalStatus.CONFIRMED_SUCCESS, external_reference="ext-99")
    )
    ctx = HandlerContext(
        authorization=auth,
        idempotency=idem,
        schema_registry=StaticSchemaRegistry(),
        workflow_id="wf-42",
        plan_id="plan-7",
    )
    h = SendNotificationHandler(context=ctx, effect_port=port)
    result = h.handle(_make_command())

    assert result.workflow_id == "wf-42"
    assert result.plan_id == "plan-7"
    assert result.authorization_decision_id is not None
    assert result.external_reference == "ext-99"


# ── Third-audit regressions ─────────────────────────────────────────────

def test_provider_sensitive_message_is_not_exposed():
    """
    Provider message containing secret-like content must not reach public result.
    Integration contract requires sanitization; Handler last-line defense also applies.
    """
    outcome = ExternalOutcome(
        status=ExternalStatus.CONFIRMED_FAILURE,
        message="Authorization failed: token=SECRET123 password=hunter2",
        provider_code="AUTH_FAIL",
    )
    h, port, _ = _handler(outcome=outcome)
    result = h.handle(_make_command())

    assert result.status == ResultStatus.FAILED
    assert result.error is not None
    assert "SECRET123" not in result.error.message
    assert "password" not in result.error.message.lower()
    assert "hunter2" not in result.error.message
    # Falls back to stable safe message
    assert result.error.message == "External system reported failure"


def test_schema_registry_exception_returns_internal_error():
    """Schema registry infrastructure failure must be INTERNAL_ERROR, not VALIDATION_ERROR."""
    class BoomSchema:
        def is_supported(self, command_type, schema_version):
            raise RuntimeError("registry unavailable")

    h, port, _ = _handler(schema_registry=BoomSchema())
    result = h.handle(_make_command())

    assert result.status == ResultStatus.FAILED
    assert result.error.category == ErrorCategory.INTERNAL_ERROR
    assert result.error.code == "SCHEMA_REGISTRY_INFRASTRUCTURE_FAILURE"
    assert len(port.calls) == 0


def test_validator_exception_returns_internal_error():
    """Unexpected exception in concrete _validate_operation must not escape handle()."""
    class BoomHandler(SendNotificationHandler):
        def _validate_operation(self, command):
            raise RuntimeError("programmer error in validator")

    idem = InMemoryIdempotency()
    port = RecordingEffectPort(
        ExternalOutcome(status=ExternalStatus.CONFIRMED_SUCCESS, external_reference="x")
    )
    ctx = HandlerContext(
        authorization=AlwaysAllowAuthorization(),
        idempotency=idem,
        schema_registry=StaticSchemaRegistry(),
    )
    h = BoomHandler(context=ctx, effect_port=port)
    result = h.handle(_make_command())

    assert result.status == ResultStatus.FAILED
    assert result.error.category == ErrorCategory.INTERNAL_ERROR
    assert result.error.code == "VALIDATION_INFRASTRUCTURE_FAILURE"
    assert len(port.calls) == 0


# ── Fourth-audit regressions ────────────────────────────────────────────

def test_malformed_external_outcome_becomes_unknown():
    """
    Effect port returns a non-ExternalOutcome object after the boundary is entered.
    Must become UNKNOWN + unresolved; retry must not re-execute.
    """
    class BadPort:
        def __init__(self):
            self.calls = []
        def execute(self, command):
            self.calls.append(command)
            return "not-an-outcome"  # malformed

    idem = InMemoryIdempotency()
    port = BadPort()
    ctx = HandlerContext(
        authorization=AlwaysAllowAuthorization(),
        idempotency=idem,
        schema_registry=StaticSchemaRegistry(),
    )
    h = SendNotificationHandler(context=ctx, effect_port=port)  # type: ignore
    cmd = _make_command(command_id="cmd-mal", idempotency_key="idem-mal")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.UNKNOWN
    assert r1.error.code == "MALFORMED_EXTERNAL_OUTCOME"
    assert len(port.calls) == 1

    # Retry must not re-execute
    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1


def test_subclass_command_is_rejected():
    """Exact type identity: subclass of declared Command type must be rejected."""
    @dataclass(frozen=True)
    class SubNotification(SendNotificationCommand):
        extra: str = "x"

    # Rebuild with required fields
    sub = SubNotification(
        command_id="cmd-sub",
        idempotency_key="idem-sub",
        schema_version="1.0",
        recipient="user@example.com",
        channel="email",
        body="hello",
        extra="oops",
    )
    h, port, _ = _handler()
    result = h.handle(sub)
    assert result.status == ResultStatus.REJECTED
    assert result.error.code == "INCOMPATIBLE_COMMAND_TYPE"
    assert len(port.calls) == 0


# ── Fifth-audit: post-effect idempotency persistence fail-closed ────────

def test_complete_failure_after_success_blocks_retry():
    """
    External effect succeeds, complete() fails.
    Port must leave key claim-refusing; retry must not re-execute.
    Result remains SUCCEEDED (truthful external outcome) with degraded flag.
    """
    idem = InMemoryIdempotency()
    idem.force_fail_complete.add("idem-cf")
    outcome = ExternalOutcome(
        status=ExternalStatus.CONFIRMED_SUCCESS,
        external_reference="ext-ok",
    )
    h, port, _ = _handler(idem=idem, outcome=outcome)
    cmd = _make_command(command_id="cmd-cf", idempotency_key="idem-cf")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.SUCCEEDED
    assert r1.metadata is not None
    assert r1.metadata.get("idempotency_complete_ok") is False
    assert r1.metadata.get("idempotency_persistence_degraded") is True
    assert len(port.calls) == 1

    # Retry must not get a second effect
    # force flag already consumed; key must remain blocked
    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1


def test_mark_unresolved_failure_after_timeout_blocks_retry():
    """
    TIMEOUT → mark_unresolved durable write fails.
    Port fail-closes (key still blocked). Retry must not re-execute.
    """
    idem = InMemoryIdempotency()
    idem.force_fail_mark_unresolved.add("idem-mu")
    outcome = ExternalOutcome(status=ExternalStatus.TIMEOUT, message="timed out")
    h, port, _ = _handler(idem=idem, outcome=outcome)
    cmd = _make_command(command_id="cmd-mu", idempotency_key="idem-mu")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.UNKNOWN
    assert len(port.calls) == 1

    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1


# ── Fifth-audit regressions: post-effect idempotency persistence fail-closed ─

def test_mark_unresolved_persistence_failure_blocks_retry():
    """
    After effect → UNKNOWN, mark_unresolved durable write fails.
    Port must still leave key claim-refusing so retry cannot re-execute.
    """
    idem = InMemoryIdempotency()
    timeout_outcome = ExternalOutcome(status=ExternalStatus.TIMEOUT, message="timed out")
    h, port, _ = _handler(idem=idem, outcome=timeout_outcome)

    cmd = _make_command(command_id="cmd-persist-u", idempotency_key="idem-persist-u")
    idem.force_fail_mark_unresolved.add("idem-persist-u")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.UNKNOWN
    assert len(port.calls) == 1
    # Persistence failure should be signaled
    assert r1.metadata is not None
    assert r1.metadata.get("idempotency_mark_unresolved_ok") is False or \
           r1.metadata.get("idempotency_persistence_degraded") is True or \
           r1.error.code == "IDEMPOTENCY_PERSISTENCE_FAILURE"

    # Critical: retry must NOT produce a second effect
    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1


def test_complete_persistence_failure_blocks_retry_after_success():
    """
    After confirmed success, complete() durable write fails.
    Port fails closed (key becomes unresolved/blocked). Retry must not re-execute.
    External outcome remains SUCCEEDED (truthfulness).
    """
    idem = InMemoryIdempotency()
    success = ExternalOutcome(
        status=ExternalStatus.CONFIRMED_SUCCESS, external_reference="ext-ok"
    )
    h, port, _ = _handler(idem=idem, outcome=success)

    cmd = _make_command(command_id="cmd-persist-c", idempotency_key="idem-persist-c")
    idem.force_fail_complete.add("idem-persist-c")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.SUCCEEDED  # truthful
    assert len(port.calls) == 1
    assert r1.metadata is not None
    assert r1.metadata.get("idempotency_complete_ok") is False or \
           r1.metadata.get("idempotency_persistence_degraded") is True

    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 1


# ── Final freeze-candidate: claim() failure contract ────────────────────

def test_claim_failure_before_ownership_no_effect():
    """claim raises before ownership → INTERNAL_ERROR, no effect, key still claimable later."""
    idem = InMemoryIdempotency()
    idem.force_fail_claim_before_own.add("idem-cb")
    h, port, _ = _handler(idem=idem)
    cmd = _make_command(command_id="cmd-cb", idempotency_key="idem-cb")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.FAILED
    assert r1.error.code == "IDEMPOTENCY_CLAIM_FAILURE"
    assert len(port.calls) == 0

    # Key was never owned → a later claim can succeed
    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.SUCCEEDED
    assert len(port.calls) == 1


def test_claim_failure_after_ownership_blocks_retry():
    """claim establishes ownership then raises → key claim-blocking; no effect; retry blocked."""
    idem = InMemoryIdempotency()
    idem.force_fail_claim_after_own.add("idem-ca")
    h, port, _ = _handler(idem=idem)
    cmd = _make_command(command_id="cmd-ca", idempotency_key="idem-ca")

    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.FAILED
    assert r1.error.code == "IDEMPOTENCY_CLAIM_FAILURE"
    assert len(port.calls) == 0

    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert r2.error.category == ErrorCategory.IDEMPOTENCY_CONFLICT
    assert len(port.calls) == 0


def test_claim_failure_cannot_produce_two_effects():
    """Under claim-after-own failure, concurrent/retry paths cannot produce two effects."""
    idem = InMemoryIdempotency()
    success = ExternalOutcome(status=ExternalStatus.CONFIRMED_SUCCESS, external_reference="x")
    port = RecordingEffectPort(success)
    ctx = HandlerContext(
        authorization=AlwaysAllowAuthorization(),
        idempotency=idem,
        schema_registry=StaticSchemaRegistry(),
    )
    h = SendNotificationHandler(context=ctx, effect_port=port)
    cmd = _make_command(command_id="cmd-2e", idempotency_key="idem-2e")

    idem.force_fail_claim_after_own.add("idem-2e")
    r1 = h.handle(cmd)
    assert r1.status == ResultStatus.FAILED
    assert len(port.calls) == 0

    # Second attempt blocked
    r2 = h.handle(cmd)
    assert r2.status == ResultStatus.REJECTED
    assert len(port.calls) == 0
