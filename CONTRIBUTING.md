# Contributing

Thank you for your interest in Handler v1.

## Project status

Handler v1 is a research-stage, owner-frozen execution subsystem. It is not presented as a complete or production-certified multi-agent orchestration platform.

## Before you contribute

- Open an issue describing the bug, documentation change, or proposal.
- Do not change frozen Handler behavior without an explicit owner-approved architectural change decision.
- Keep test doubles distinct from production adapters.
- Do not introduce direct agent-to-tool execution paths, implicit retries, privilege escalation, or disclosure of untrusted provider exception details.

## Development

From the repository root:

```bash
cd Handlerv1
python -m pip install -e ".[test]"
python -m pytest handler_v1/tests/ -q
```

For code changes, provide a focused test, explain any changed invariants, and request review. Security-sensitive changes should be accompanied by adversarial test cases. No direct commits to the frozen source are authorized by this file.

## Security reports

Do not publish undisclosed exploitable security findings as public issues. Contact the maintainer privately using GitHub's available private reporting channels when enabled.

## Historical artifacts

The project's architecture and audit materials are historical evidence. Preserve them rather than deleting them for cosmetic reasons.
