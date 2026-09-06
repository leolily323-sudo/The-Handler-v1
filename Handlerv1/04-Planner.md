# Planner — Frozen Contract

**Status:** FROZEN  
**Final targeted review completed; ambiguities resolved.**

---

## Primary Principle

The Planner is a **proposal generator**, not an authority mechanism.

It may determine what work should be attempted, how to decompose goals, dependencies, required inputs/outputs, contingencies, alternatives, estimates, etc.

It MUST NOT determine authorization, capability existence, policy bypass, approval skipping, tool execution, spending permission, completion, or Event emission.

---

## Key Design Decisions

### Output
Immutable, typed `ExecutionPlan` artifact (semantic content is deterministic and content-addressed).

- `plan_id` = artifact identity (may be runtime-generated)
- `lineage_id` + `version` = logical planning thread
- `semantic_hash` = deterministic identity of pure plan content
- Re-planning always creates a new immutable artifact with parent pointer.

### Input Boundary
Narrow `PlannerContext` containing only projected, already-authorized, immutable views.  
Raw LLM output is forbidden as authoritative input.

### LLM Boundary
```
LLM (untrusted) → CandidatePlan → schema + semantic validation → Normalized ExecutionPlan
```
Only the normalized ExecutionPlan proceeds.

### Command Boundary
Plan nodes reference only Commands that exist in the typed Command Registry.  
A plan never carries authorization. Every materialized Command is re-authorized at execution time.

### Preconditions
Declared by Planner; evaluated by Scheduler/Handler against **current** live projections.  
Stale assumptions never override current state.

### Blocked Nodes
Deterministic rule: omit + produce alternative, **or** include marked `blocked_by` and mark plan `partially_blocked`.  
A blocked node inside a plan still carries zero authority.

### Policy / Capability in Context
Supplied only as constraints / provenance (`PolicyConstraint`).  
Never treated as durable authorization tokens.

### Provenance
Descriptive only. Never interpreted downstream as authority.

---

## Authority Invariants (Proven)

- Cannot grant, manufacture, or infer capabilities.
- Cannot override DENY, bypass REQUIRE_APPROVAL, or reverse ATTENUATE.
- Cannot invent arbitrary Command types.
- Cannot mutate workflow state or emit Events.
- Cannot execute tools.
- Historical plans remain inspectable without re-invoking the LLM.

---

**This contract is frozen.**
