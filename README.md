# Handler V1: Deterministic Control Plane & Safety Gateway for AI Agents

`handler_v1` is a Python-based execution control plane designed to bridge non-deterministic AI decisions (LLM outputs, dynamic planners) with deterministic real-world system execution.

It uses a **Hexagonal (Ports-and-Adapters)** architecture to enforce authorization, idempotency, and explicit external-effect boundaries for commands routed through the Handler. Integrations must ensure agents cannot bypass that boundary.

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

- **`Handlerv1/handler_v1/core/handler.py`**: The primary command pipeline that manages the lifecycle of incoming execution requests.
- **`Handlerv1/handler_v1/ports/authorization.py`**: Enforces policy permissions before execution.
- **`Handlerv1/handler_v1/ports/idempotency.py`**: Prevents duplicate execution by checking idempotency keys and state tokens.
- **`Handlerv1/handler_v1/ports/external_effect.py`**: Isolates side effects, logging and capturing external system interactions.
- **`Handlerv1/handler_v1/results/execution_result.py`**: Formats deterministic execution outputs returned to the caller.

---

## Security Model & Execution Boundary

The central security invariant of `handler_v1` is:

**An AI agent may propose an action, but it does not have authority to execute that action directly.**

The intended execution path is:

**LLM / Agent → Proposed Command → Handler → Authorization → Idempotency → External Effect Boundary → External System**

The Handler exposes no supported direct LLM-to-effect path. An integrating application must separately ensure that agents cannot bypass the Handler.

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

### Requirements

- Python 3.10+ (recommended; the source uses modern type annotations)
- `pytest` to run the tests

Clone the repository, enter the folder containing the Python package, and install the test runner:

```bash
git clone https://github.com/leolily323-sudo/The-Handler-v1.git
cd The-Handler-v1/Handlerv1
python -m pip install -e ".[test]"
```

The included authorization, idempotency, and effect adapters are **in-memory test doubles**, not production-ready integrations. The Python package is installable from the `Handlerv1/` directory; publishing it to a package index is not yet part of this release.

### Basic usage (safe local demonstration)

This example records an intended notification in memory. It does **not** send an email or call an external API.

```python
from handler_v1.commands.example_commands import SendNotificationCommand
from handler_v1.core.handler import HandlerContext
from handler_v1.core.notification_handler import SendNotificationHandler
from handler_v1.ports.in_memory import (
    AlwaysAllowAuthorization,
    InMemoryIdempotency,
    RecordingEffectPort,
)
from handler_v1.ports.schema import StaticSchemaRegistry
from handler_v1.ports.external_effect import ExternalOutcome, ExternalStatus

context = HandlerContext(
    authorization=AlwaysAllowAuthorization(),
    idempotency=InMemoryIdempotency(),
    schema_registry=StaticSchemaRegistry(),
)
effect = RecordingEffectPort(
    ExternalOutcome(
        status=ExternalStatus.CONFIRMED_SUCCESS,
        external_reference="demo-record-1",
    )
)
handler = SendNotificationHandler(context=context, effect_port=effect)

command = SendNotificationCommand(
    command_id="demo-command-1",
    idempotency_key="demo-operation-1",
    schema_version="1.0",
    recipient="example@example.com",
    channel="email",
    body="Hello from the local Handler demo",
)
result = handler.handle(command)
print(result.status.value)
print("Effect calls recorded:", len(effect.calls))
```

Expected output:

```text
SUCCEEDED
Effect calls recorded: 1
```

For real deployments, inject authorization and durable idempotency adapters with the contracts documented in [FINAL-STATUS.md](Handlerv1/handler_v1/FINAL-STATUS.md). A successful in-memory demonstration is not proof of end-to-end production safety.

---

## Testing

From `The-Handler-v1/Handlerv1`:

```bash
python -m pytest handler_v1/tests/ -q
```

The repository includes lifecycle and regression tests for rejection paths, concurrent idempotency claims, unknown external outcomes, and post-effect failure handling. Historical audit results should be distinguished from a fresh test run against the current commit.

### Project documentation

- [Implementation notes](Handlerv1/handler_v1/IMPLEMENTATION_NOTES.md)
- [Handler status record](Handlerv1/handler_v1/FINAL-STATUS.md)
- [Architectural project state](Handlerv1/CURRENT-STATE.md)
- [Handler blueprint](Handlerv1/Handler%20Blueprint%20v1.txt)

The linked status records are historical freeze-candidate documents dated August 18, 2026. They are retained as project history and should not be mistaken for a current independent audit.

---

## Contributing and roadmap

- [Contributing guidelines](CONTRIBUTING.md)
- [Project roadmap](ROADMAP.md)

The published Handler is a research-stage subsystem with owner-frozen execution logic, not a complete production-certified orchestrator. Contributions to architecture or behavior require explicit review against the frozen contracts.

---

## License

MIT License. Free for open-source and commercial use.
