# Policy Engine — Frozen Contract

**Status:** FROZEN  
**Audited and locked after full architectural review.**

---

## Core Invariant

Capability establishes the maximum authority.  
Policy may only **restrict, attenuate, gate, or require approval**.  
Policy may never grant authority or convert Capability DENY → ALLOW.

---

## Evaluation Model

- Pure, deterministic function.
- Produces non-durable `Decision` / `PolicyEvaluation` objects.
- Durable outcomes are still emitted only by the Command handler as Events.

### Pipeline Position

```
Command → Schema Validation → Capability Check → Policy Evaluation → Combine → Handler / Approval / Rejection
```

### Effects

- ALLOW
- DENY
- REQUIRE_APPROVAL
- ATTENUATE
- ESCALATE

### Decision Combination (deterministic total order)

DENY > ESCALATE > REQUIRE_APPROVAL > ATTENUATE > ALLOW

Attenuations are merged monotonically (registered per-key strategies: min for numeric limits, intersection for sets, etc.). Unknown keys rejected at install time.

### No-match / Failure Semantics

- Fail-closed: evaluation errors → DENY.
- No applicable policies → inherit Capability Decision.
- Policy applies but no rules match → that policy contributes ALLOW.

### Temporal Correctness

Every Command records the exact `policy_snapshot_id` (or set of policy_id+version) used.  
Replay uses the historical snapshot, never the current active set.

### Condition Language

Restricted deterministic expression language / AST.  
Validated and compiled at policy installation time. No arbitrary Python, no I/O, no mutation, no network.

### Versioning & Installation

Policies are immutable versioned artifacts.  
Install / enable / disable are themselves Commands that travel through the normal Capability + Policy path.  
Foundational policies can be marked non-overridable.

---

**This contract is frozen.**
