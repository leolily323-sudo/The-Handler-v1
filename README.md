# Handler v1

This repository contains Handler v1, a deterministic execution boundary for AI-proposed commands.

Handler v1 is a small, research-stage Python control plane designed to keep AI systems from directly crossing into sensitive or irreversible execution paths. It enforces an explicit lifecycle: propose → authorize → claim idempotency → execute through a typed effect boundary → classify the outcome.

## What Handler v1 does

Handler v1 gives an AI agent a structured execution contract instead of direct access to external systems.

The core idea is simple:

- an AI can propose a command,
- the application verifies that the command is allowed,
- the system checks whether the same action is already in flight or already completed,
- only a narrow, typed effect path is allowed to act on the outside world.

That makes the project useful for teams who want a fail-closed boundary around automated command execution.

## The problem it solves

Without a boundary, an AI system can:

- propose invalid or unsafe actions,
- retry the same effect multiple times,
- bypass normal authorization checks,
- produce side effects without clear control or auditability.

Handler v1 is meant to reduce that risk by making the execution path explicit, deterministic, and testable.

## Who this is for

This repo is most relevant to:

- researchers building agent execution controls,
- developers designing safety boundaries around LLM-driven workflows,
- teams prototyping policy enforcement before production integrations,
- maintainers who want a small, auditable command-execution model.

This is not a general-purpose orchestration platform or a production-certified control plane.

## Current maturity

Handler v1 is best described as:

- a research-stage Python subsystem,
- owner-frozen in its core runtime behavior,
- documented for public review and maintainer onboarding,
- suitable for local demonstration and regression testing,
- not presented as a complete enterprise-ready distributed control plane.

The architectural freeze is intentional. The project law in `Handlerv1/00-Project-Law-and-Session-Transition.md` and the freeze record in `Handlerv1/HANDLER-V1-FREEZE-AND-VERIFICATION.md` define non-negotiable constraints.

## Installation

From the repository root:

```bash
git clone https://github.com/leolily323-sudo/The-Handler-v1.git
cd The-Handler-v1/Handlerv1
python -m pip install -e ".[test]"
```

This installs the package in editable mode and includes the `pytest` test dependency.

## Test the project

From `The-Handler-v1/Handlerv1`:

```bash
python -m pytest handler_v1/tests/ -q
```

The repo also includes a GitHub Actions workflow at `.github/workflows/handler-tests.yml` that validates:

- editable install,
- source and wheel build,
- regression lifecycle tests.

## Run a local demonstration

From the repository root:

```bash
PYTHONPATH=Handlerv1 python examples/local_demo.py
```

The demo uses the project’s in-memory authorization, idempotency, and effect ports to show the expected control-flow pattern without calling external services.

Expected output is similar to:

```text
SUCCEEDED
Effect calls recorded: 1
```

## Safety boundaries enforced by Handler v1

The project addresses a narrow but important safety boundary:

- AI output is treated as untrusted input.
- execution requires a typed command contract,
- authorization is checked at execution time,
- idempotency claims protect against duplicate execution,
- external effects occur only through the effect boundary,
- outcomes are classified as succeeded, failed, rejected, or unknown.

These are design protections, not guarantees that every external system or upstream prompt is safe.

## What this repo is not claiming

This repository does not claim:

- production certification,
- broad deployment coverage,
- enterprise support,
- a stable external API beyond the frozen v1 design,
- universal safety against every agent or infrastructure failure.

## Where the project is going

The public roadmap is intentionally modest and subject to owner approval:

- confirm verified installation and CI evidence,
- improve contributor onboarding,
- add clearer examples and security guidance,
- keep the architectural core frozen while improving external docs and usability.

See `ROADMAP.md` and `docs/README.md` for the current project direction.

## Additional docs

- `docs/README.md` — public documentation layout and navigation
- `docs/CODEX_OSS_APPLICATION_EVIDENCE.md` — evidence prepared for application review
- `CONTRIBUTING.md` — contributor expectations and local workflow
- `SECURITY.md` — vulnerability reporting guidance
- `Handlerv1/00-Project-Law-and-Session-Transition.md` — project law and session transition rules
- `Handlerv1/HANDLER-V1-FREEZE-AND-VERIFICATION.md` — historical freeze and verification record

## License

MIT License.
