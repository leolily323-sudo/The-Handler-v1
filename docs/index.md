# Handler v1 — Ports & Contracts (docs)

This small docs index explains the required ports you'll need to implement when integrating Handler v1.

Ports

- AuthorizationPort
  - authorize(command) -> AuthorizationDecision
  - Must return decision.is_allowed and decision_id

- IdempotencyPort
  - claim(idempotency_key, command_id) -> IdempotencyClaimResult
  - complete(idempotency_key, command_id, outcome_reference)
  - mark_unresolved(idempotency_key, command_id)
  - release(idempotency_key, command_id)

- ExternalEffectPort
  - execute(command) -> ExternalOutcome
  - Must return ExternalOutcome with status in ExternalStatus

- SchemaRegistryPort
  - is_supported(command_type, schema_version) -> bool

How to run tests

1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements-dev.txt
4. pytest
