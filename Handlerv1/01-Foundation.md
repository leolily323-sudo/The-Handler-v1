# Foundation — Frozen Contract

**Status:** FROZEN  
**Last audited:** Multiple refinement passes completed; locked before Capability System work began.

---

## Core Invariants (Non-Negotiable)

- The LLM is an untrusted probabilistic component.
- The Python control plane owns all authority.
- Agents never determine their own permissions, completion, or routing.
- Agents only propose candidate outputs.
- Every mutation must be deterministic.
- Every important action must be replayable and auditable.
- Every external side effect must be idempotent.
- The event history is the source of truth. Snapshots are performance optimizations only.
- Security always overrides convenience.
- Determinism always overrides intelligence.

---

## Key Decisions Locked

### Typed Event Registry
- Every event type owns an immutable, versioned Pydantic payload schema.
- Central registry maps `(EventType, schema_version) → payload model`.
- Unknown or mismatched schemas are rejected at the boundary.
- `payload: dict[str, Any]` is forbidden.

### Typed Command Registry
- Mirrors the Event Registry.
- Every command has its own immutable payload schema and version.
- Commands are the *only* legal mutation entry point.

### Pure Immutable Reducers
- `new_state = reducer(old_state, event)`
- All state objects are frozen.
- No in-place mutation.

### Aggregate Invariants
- Enforced after every reduction during replay.
- Violation aborts replay (indicates bug or corruption).

### Separate Integrity Layer
- Cryptographic signatures, verification, and key management live outside the EventStore.
- EventStore is a pure durable, ordered, content-addressed log.

### Vector Clocks
- Explicitly removed from MVP. Per-stream monotonic sequence + hash chain is sufficient until distributed writers exist.

### Command Pipeline
```
Command → Schema Validation → Policy → Capability → Handler → Event(s) → Integrity → Store → Projection
```
(Note: later refined so Capability and Policy order is Capability first as authority ceiling, then Policy as restriction.)

### Decision vs Event
- Policy and Capability produce non-durable `Decision` objects.
- Only durable outcomes become Events.

---

## Dependency Order (Locked)

1. Event Store + typed registries + pure reducers + Integrity Layer
2. Command Layer
3. Capability System
4. Policy Engine
5. Planner
6. Scheduler
7. Handler
8. …

---

**This contract is frozen. Changes require explicit architectural decision by the Project Owner.**
