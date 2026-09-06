# Handler V1: Deterministic Control Plane & Safety Gateway for AI Agents

`handler_v1` is a Python-based execution control plane designed to bridge non-deterministic AI decisions (LLM outputs, dynamic planners) with deterministic real-world system execution.

It enforces a **Hexagonal (Ports-and-Adapters)** architecture to guarantee that no AI action reaches external infrastructure without passing strict authorization, idempotency, and side-effect boundaries.

---

## The Problem It Solves

When AI agents execute commands directly against production systems:
1. **Hallucinations & Invalid State:** Unconstrained outputs can trigger unvalidated API calls or invalid system mutations.
2. **Duplicate Side-Effects:** Retried agent actions can run duplicate tasks, leading to race conditions or financial loss.
3. **Privilege Escalation:** LLMs lack hardcoded execution limits, making them vulnerable to prompt injection or unauthorized operations.

`handler_v1` acts as a **circuit breaker and safety gateway**: the AI acts as the *Planner*, while `handler_v1` serves as the deterministic *Dispatcher*.

---

## Core Architecture

```
                    ┌───────────────────────────┐
                    │  AI Agent / LLM Planner   │
                    └─────────────┬─────────────┘
                                  │ Proposed Command
                                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                           HANDLER V1 CORE                             │
│                                                                       │
│   ┌───────────────────┐    ┌───────────────────┐    ┌─────────────┐   │
│   │ AuthorizationPort │ ──►│  IdempotencyPort  │ ──►│ EffectPort  │   │
│   └───────────────────┘    └───────────────────┘    └─────────────┘   │
│                                                             │         │
│                                                             ▼         │
│                                                  ┌────────────────┐   │
│                                                  │ Core Execution │   │
│                                                  └────────────────┘   │
└──────────────────────────────────────────────┬────────────────────────┘
                                               │ Verified Execution
                                               ▼
                                   ┌───────────────────────┐
                                   │ External System / API │
                                   └───────────────────────┘
```

### Module Breakdown

- **`handler_v1/core/handler.py`**: The primary command pipeline that manages the lifecycle of incoming execution requests.
- **`handler_v1/ports/authorization.py`**: Enforces policy permissions before execution.
- **`handler_v1/ports/idempotency.py`**: Prevents duplicate execution by checking idempotency keys and state tokens.
- **`handler_v1/ports/external_effect.py`**: Isolates side effects, logging and capturing external system interactions.
- **`handler_v1/results/execution_result.py`**: Formats deterministic execution outputs returned to the caller.

---

## Security Model & Execution Boundary

The central security invariant of `handler_v1` is:

**An AI agent may propose an action, but it does not have authority to execute that action directly.**

The intended execution path is:

**LLM / Agent → Proposed Command → Handler → Authorization → Idempotency → External Effect Boundary → External System**

There is no supported execution path in which an untrusted LLM output directly reaches external infrastructure.

This separation is deliberate:

- **LLM / Agent:** proposes what should happen. Its output is treated as untrusted input.
- **Command:** gives the proposal a structured execution contract.
- **Authorization:** determines whether the proposed command is permitted at execution time.
- **Idempotency:** prevents the same command from being executed repeatedly when the same operation is retried or duplicated.
- **External Effect Boundary:** isolates and records interactions with systems outside the control plane.
- **Core Execution:** performs the already-authorized operation through the defined interfaces.

### Security Guarantees

Handler v1 is designed to guarantee the following control-plane properties:

1. **Untrusted AI boundary** — AI output does not itself constitute execution authority.
2. **Execution-time authorization** — permission is checked before the operation is allowed to proceed.
3. **Duplicate-execution protection** — idempotency controls are applied before external side effects.
4. **Side-effect isolation** — external interactions occur through the explicit effect boundary rather than arbitrary AI/tool behavior.
5. **Deterministic control flow** — the Handler controls the execution lifecycle rather than allowing the LLM to decide how infrastructure is accessed.

### What Handler v1 Does Not Claim

Handler v1 is a deterministic safety gateway, not a guarantee that every external system is transactional, correct, or failure-proof.

In particular, the Handler does not by itself guarantee:

- that an authorized command is desirable or semantically correct;
- that an external system will successfully perform an operation;
- that an external system will never fail after receiving a request;
- distributed transactional guarantees that are not provided by the external system or integration;
- that every possible security problem in an AI system is solved by the Handler alone.

The Handler's responsibility is narrower and more defensible:

**Control whether a proposed operation is allowed to cross the execution boundary, and ensure that crossing happens through the defined deterministic lifecycle.**

---

## Quickstart

### 1. Installation

```bash
git clone <REPOSITORY_URL>
cd handler_v1
pip install -r requirements.txt
```

### 2. Basic Usage

```python
from handler_v1.core.handler import CommandHandler
from handler_v1.commands.example_commands import SystemActionCommand
from handler_v1.ports.in_memory import InMemoryPortAdapter

# Initialize Handler with safety ports
ports = InMemoryPortAdapter()
handler = CommandHandler(ports=ports)

# Define an action proposed by an AI agent
command = SystemActionCommand(
    action_id="cmd_98234",
    idempotency_key="idempotent_key_abc123",
    payload={"action": "restart_service", "target": "auth_db"}
)

# Dispatch through deterministic control plane
result = handler.dispatch(command)

if result.is_success:
    print(f"Command Executed Safely: {result.data}")
else:
    print(f"Blocked by Control Plane: {result.error}")
```

---

## Testing

Run the full automated test suite verifying lifecycle safety, port rejection, and idempotency checks:

```bash
pytest handler_v1/tests/test_handler_lifecycle.py
```

---

## License

MIT License. Free for open-source and commercial use.
