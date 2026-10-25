# Handler v1: Codex OSS application evidence

## Scope

This document records the current public-facing evidence for Handler v1 as a research-stage open-source project. It distinguishes project history from currently reproducible evidence.

## 1. Project purpose and technical significance

Handler v1 is a deterministic execution boundary for AI-proposed commands. The project implements a narrow but important safety layer:

- AI output is treated as untrusted input,
- typed commands are validated before execution,
- authorization is checked at execution time,
- idempotency claims prevent duplicate effects,
- the external effect boundary is isolated and typed,
- outcomes are reduced to a controlled result model.

This matters in agentic systems where an LLM or planner can propose actions but should not directly control external side effects without explicit execution controls.

## 2. Existing implemented capabilities

The current repository contains a documented execution model and a runnable Python implementation for the core control-flow boundary, including:

- `Handlerv1/handler_v1/core/handler.py` — central handler lifecycle with fail-closed checks,
- `Handlerv1/handler_v1/core/notification_handler.py` — example concrete handler,
- `Handlerv1/handler_v1/ports/authorization.py` — authorization decision contract,
- `Handlerv1/handler_v1/ports/idempotency.py` — idempotency claim and persistence contracts,
- `Handlerv1/handler_v1/ports/external_effect.py` — typed external side-effect boundary,
- `Handlerv1/handler_v1/ports/in_memory.py` — local, process-in-memory demonstration adapters,
- `Handlerv1/handler_v1/commands/example_commands.py` — example command type for local demonstration.

This is a functioning local control-plane prototype, not a broad production orchestration system.

## 3. Verified tests and CI

The repository includes a dedicated GitHub Actions workflow:

- `.github/workflows/handler-tests.yml`

Current workflow runs indicate the repository is passing the tests in CI as of the latest observed run:

- Run ID: `40147845957`
- Workflow: `Handler v1 tests`
- Conclusion: `success`
- Head SHA: `25fc5bdc33f5d79cb53fe8d486fa827a6c6b7d19`

The workflow validates:

- editable package install via `python -m pip install -e ".[test]"`
- build artifacts via `python -m build --wheel --sdist`
- regression suite via `python -m pytest handler_v1/tests/ -q`

This evidence is currently reproducible via GitHub Actions and should be linked directly to the exact commit before making application claims.

## 4. Known limitations

The project is intentionally constrained and presently limited in several ways:

- the implementation is a research-stage subsystem, not a production-certified platform,
- the public package is small and narrow in scope,
- external integrations are intentionally abstracted; production adapters are not included in the public package,
- the in-memory ports are demonstration/test adapters, not durable production services,
- the repository does not currently claim broad deployment or enterprise adoption metrics.

## 5. Development and maintenance history

The project includes a clear historical record that distinguishes design freeze records from current public-facing maintenance work:

- `Handlerv1/00-Project-Law-and-Session-Transition.md` records the active project law and transition rules,
- `Handlerv1/HANDLER-V1-FREEZE-AND-VERIFICATION.md` records freeze status and verification procedure,
- `Handlerv1/Handler Blueprint v1.txt` preserves the historical blueprint,
- PR #1 was a packaging and contributor-onboarding hardening patch for public repository presentation.

This history supports the project’s public maturity work without altering the frozen runtime specification.

## 6. Public usage or adoption evidence

No verified public adoption metrics, deployment record, or usage metrics are currently claimed in this repository.

The project should not invent or imply:

- production deployments,
- third-party endorsements,
- significant ecosystem adoption,
- public user counts or enterprise traction.

## 7. Why this project could benefit from Codex

This project has a strong fit for maintainer workflows that benefit from structured support:

- issue triage and maintenance support,
- documentation review and cleanup,
- regression test expansion,
- onboarding assistance for new contributors,
- packaging and release hygiene,
- repetitive maintainer tasks around project clarity and evidence preparation.

The repository is small enough to benefit from focused automation while still needing human architectural review and owner approval.

## 8. Evidence gaps before a final application

The following items remain as open evidence gaps:

- verify current official OpenAI eligibility requirements before a final submission,
- confirm public maintainer role and ownership details,
- confirm a final public repo maturity narrative that fits the selected program terms,
- document any external adoption or ecosystem impact if it exists and can be verified,
- keep the historical freeze records clearly separated from current public documentation.

## 9. Current OpenAI eligibility note

OpenAI’s public program documentation indicates that applicants should be active maintainers of public open-source projects with meaningful ecosystem importance, and that public GitHub profile and repository visibility are required. Those conditions should be re-verified against the current official program terms before the project owner submits an application.

This requirement is recorded here as a verification step, not as an unverified claim about current program acceptance.
