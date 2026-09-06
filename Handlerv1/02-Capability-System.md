# Capability System — Frozen Contract

**Status:** FROZEN

---

## Purpose

Capability System establishes the **maximum authority** any principal may exercise.

Policy may only further restrict, attenuate, or gate that authority.  
Policy may never grant a capability or convert a Capability DENY into ALLOW.

---

## Core Model

- Capabilities are first-class, versioned, auditable values.
- Issued and revoked only through typed Commands that themselves pass authorization.
- Support: fine-grained permissions, temporary/expiring, scoped, delegatable with attenuation, immediate revocation, full audit trail.
- No privilege-escalation paths: delegation can only attenuate or keep the same permissions.

### Key Types (conceptual)

- `Permission` — action + resource + constraints
- `Capability` — id, principal, issuer, permissions, scope, issued_at, expires_at, delegatable, attenuation
- `CapabilityState` — projected active + revoked sets

### Check API

Pure function:

```text
check_capability(state, principal_id, required_permission, context) → Decision
```

Decision is non-durable. Only the final accept/reject of a Command produces durable Events.

---

## Invariants

- A capability may only be issued by a principal that already holds authority to issue it (or by bootstrap root).
- Once revoked, a capability_id can never be re-activated.
- Expired capabilities are treated as absent.
- Capabilities are never stored inside agent prompts as authoritative; the control plane always re-checks against projected state.
- Single root capability is injected at system initialization via signed bootstrap event. All others derive from it.

---

## Security Properties

- Prompt injection cannot escalate privilege because the LLM never holds real capabilities.
- Even a compromised agent can only exercise previously issued capabilities.
- Revocation is immediate on next projection.

---

**This contract is frozen.**
