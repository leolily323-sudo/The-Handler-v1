# Handler v1 — FINAL STATUS

**Artifact version:** Handler v1 FREEZE CANDIDATE  
**Date:** 2026-08-18  
**Blueprint:** Handler Blueprint v1.txt (binding)

---

## Implementation status

**FREEZE CANDIDATE — pending independent final audit.**

Not frozen. Freeze authority belongs solely to the Project Owner after independent audit.

---

## Lifecycle (implemented)

```
exact Command type
  → validation (structural + operation)
  → schema validation (injected SchemaRegistryPort)
  → fresh authorization (injected AuthorizationPort)
  → atomic idempotency claim (injected IdempotencyPort)
  → external effect (injected ExternalEffectPort)
  → outcome classification
  → terminal / unresolved idempotency state
  → ExecutionResult
```

No external effect before authorization + successful claim.  
No automatic retry inside the Handler.

---

## Idempotency guarantees

### Atomic claim
- Under concurrency, at most one caller obtains `CLAIMED` for a key.
- `claim()` failure contract:
  - **Before ownership:** exception; key remains unclaimed (safe to retry claim).
  - **After ownership established:** exception; key left claim-blocking (`UNRESOLVED`); no second `CLAIMED`.
  - No ambiguous reclaimable partial-ownership gap.

### Post-effect persistence
- `complete()` / `mark_unresolved()` succeed durably or raise `IdempotencyPersistenceError`.
- On failure, key remains claim-blocking (fail-closed).
- Truthful external outcome preserved (`SUCCEEDED` stays `SUCCEEDED`; `UNKNOWN` stays `UNKNOWN`).
- Persistence failure surfaced in metadata / `IDEMPOTENCY_PERSISTENCE_FAILURE`.

### UNKNOWN / crash window
- Timeout, ambiguous, effect exception, malformed outcome → `UNKNOWN`.
- `UNKNOWN` is claim-blocking; automatic retry cannot re-execute.

---

## Result semantics

| Situation | Result |
|-----------|--------|
| Confirmed success | SUCCEEDED |
| Confirmed external failure | FAILED |
| Validation / auth / idempotency refusal | REJECTED |
| Timeout / ambiguous / effect exception / malformed outcome | UNKNOWN |
| Infrastructure failure before effect | FAILED / INTERNAL_ERROR |

Public results do not contain raw exception strings, stack traces, or secrets.

Provenance: `authorization_decision_id`, `capability_snapshot_id`, `policy_snapshot_id` propagated when available.

---

## Test status

Command: `python -m pytest handler_v1/tests/ -q`

Expected: all pass, 0 failures, 0 errors.

---

## Production adapter assumptions

- `IdempotencyPort` must provide deployment-appropriate atomic claim + durable complete/mark_unresolved with the fail-closed contracts above.
- `ExternalEffectPort` adapters must sanitize `message` / `provider_code` before constructing `ExternalOutcome`.
- `SchemaRegistryPort` is owned by the Command Registry / Foundation layer, not the Handler.
- Recovery/reconciliation workers live outside the Handler.

---

## Files in freeze-candidate package

- `handler_v1/` — implementation, ports, results, tests, notes, this status
- `Handler Blueprint v1.txt`
- `CURRENT-STATE.md`
- `00-Project-Law-and-Session-Transition.md`
- `01-Foundation.md` … `05-Scheduler.md`

---

**FREEZE CANDIDATE — pending independent final audit.**
