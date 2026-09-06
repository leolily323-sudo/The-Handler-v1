# Scheduler — Frozen Contract

**Status:** FROZEN

---

## Primary Responsibility

Turn eligible nodes of an immutable `ExecutionPlan` into typed Commands and submit them to the normal authorization pipeline.  
Coordinate ordering, concurrency, retries, claims, and recovery.

**The Scheduler is NOT an authorization system, NOT an execution engine, NOT a Policy Engine, and NOT a Capability System.**

---

## Key Rules

### Materialization
```
eligible PlanNode
  → re-check preconditions against live projections
  → resolve Command type from Registry (must exist)
  → validate payload
  → apply only Policy-authorized attenuations
  → create typed Command (new command_id + link to plan_node + attempt)
  → submit to Capability → Policy → Handler
```

### Authorization Timing
Re-authorize (Capability + Policy) at materialization **and** immediately before dispatch to Handler.  
Earlier authorization is never treated as permanent.

### Preconditions & Stale State
Re-evaluated against current authoritative projections before materialization.  
Failure blocks the node and may trigger re-planning. Plans are never mutated.

### Retries & Idempotency
- Explicit idempotency key per logical operation.
- Distinguish safe-to-retry vs unknown external outcome.
- Unknown outcome does **not** automatically retry.
- Retry limits, backoff, and safety classified by Policy + Command contract.

### Concurrency & Leases
Durable claims (via Commands/Events).  
Fencing tokens prevent double dispatch.  
Scheduler may tighten concurrency limits; it may never loosen Policy/Capability limits.

### Time
All time-dependent decisions receive explicit `scheduling_time` from context.  
No hidden `datetime.now()` inside pure eligibility logic.

### Cancellation
Plan/node cancellation is durable.  
Queued/claimed work can be cancelled.  
In-flight cancellation is best-effort signal to Handler.

### Re-planning
Scheduler may emit `RequestReplanCommand`.  
It never modifies an existing plan or invents nodes.

### Durability
All durable scheduling state is projected from the existing Event architecture.  
No side mutable coordination store.

---

## Authority Invariants

- Cannot grant capabilities or bypass Policy.
- Cannot weaken attenuations.
- Cannot treat Plan provenance as authorization.
- Cannot execute tools or mutate workflow state directly.

---

**This contract is frozen.**
