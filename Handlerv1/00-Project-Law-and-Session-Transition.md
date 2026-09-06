# Project Law & Session Transition Law

**Status:** ACTIVE PROJECT LAW  
**Applies to:** Every ChatGPT and Grok session associated with this project  
**Purpose:** Prevent loss, corruption, contradiction, or accidental redesign of project knowledge during session transitions.

---

## 1. Core Law

No project session is authoritative merely because it is the newest conversation.

The project’s authoritative state is defined by its controlled project artifacts and explicit state records.

Conversation history is working context, not the permanent source of truth.

A new session must never assume that forgotten, ambiguous, or conflicting conversational context is correct.

---

## 2. The Punch-In / Punch-Out Routine

### PUNCH-IN

Before substantive project work begins:

1. Load the current Project Source of Truth.
2. Identify the current project state.
3. Identify frozen architecture.
4. Identify the active work item.
5. Identify unresolved issues.
6. Identify known deviations between specification and implementation.
7. Identify the current role of each participant.
8. Confirm that no previous-session instruction conflicts with the authoritative artifacts.
9. Establish what must not be changed during the session.
10. Only then begin work.

### PUNCH-OUT

Before ending or transitioning a session:

1. Stop substantive work.
2. Determine exactly what changed.
3. Separate: completed work, proposed work, rejected work, unresolved questions, discovered risks, implementation deviations.
4. Record all decisions that became authoritative.
5. Record all decisions that remain provisional.
6. Record every newly discovered issue that could affect future work.
7. Update the appropriate project artifact(s).
8. Verify that no secrets, credentials, private data, or accidental temporary material became part of the project state.
9. Establish the exact next starting point.
10. Produce the Session Handoff Record.
11. Do not claim the transition is complete until the handoff is internally consistent.

---

## 3. Source-of-Truth Hierarchy

When information conflicts, resolve it in this order:

1. Explicit current project law
2. Frozen architectural charters / specifications
3. Approved implementation contracts and schemas
4. Latest validated project-state record
5. Audited implementation
6. Session handoff record
7. Conversation history
8. Memory / recollection
9. Assumptions

Lower-level information may never silently override higher-level information.

If two authoritative artifacts conflict, STOP. The conflict becomes an explicit unresolved issue.

---

## 4. Frozen Means Frozen

A component marked FROZEN cannot be redesigned, weakened, removed, or behaviorally altered merely because a new session has begun, a different model proposes a cleaner design, an implementation becomes inconvenient, or a new idea appears.

A frozen component may only be changed through an explicit architectural change decision that states what is changing, why, which invariants are affected, which dependencies are affected, and what existing work becomes invalid.

No silent architectural drift.

---

## 5. No Assumption Recovery

When a new session encounters missing information: DO NOT GUESS.

Identify missing information → locate authoritative artifact → verify → continue.  
If it cannot be verified: Mark UNKNOWN → preserve the uncertainty → ask for resolution when necessary.

---

## 6. State Classification

Every important project statement is one of:

- **AUTHORITATIVE** — Approved project truth
- **PROVISIONAL** — Current proposal not yet accepted
- **REJECTED** — Explicitly discarded
- **UNKNOWN** — Insufficient information

---

## 7. Role Separation

- **User / Project Owner** — Final authority over direction, acceptance of major decisions, freeze decisions, priorities.
- **ChatGPT** — Architectural auditor, adversarial reviewer, consistency checker, security reviewer, specification critic.
- **Grok** — Builder / implementation engineer within assigned scope. Must not silently redefine frozen architecture.

Neither model may treat its own generated output as authoritative merely because it generated it.

---

## 8–19. (Full text of the law is preserved in the original Session Transition Law document. This file is the authoritative copy for project use.)

**Golden Rule:** Continuity over convenience.  
**Enforcement:** The artifacts remember. The models reason. The owner decides. The control architecture enforces.

**STATUS:** SESSION TRANSITION LAW — ACTIVE
