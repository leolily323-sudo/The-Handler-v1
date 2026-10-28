# Security Policy

## Supported versions

This repository is maintained in a research-stage, owner-frozen state. The project does not currently publish a formal compatibility matrix for multiple supported release branches.

## Reporting a vulnerability

If you believe you have found a security issue in the Handler v1 project:

1. Do not open a public issue containing exploitation details.
2. Contact the maintainer directly through GitHub and request a private disclosure path.
3. Provide a concise description of the issue, affected files or modules, and a reproduction path if available.
4. Allow a reasonable time for review before discussing the issue publicly.

The key principle is responsible disclosure: public issue trackers are for non-sensitive project discussion, while security flaws should be handled privately.

## Security scope

This project’s security boundary is intentionally narrow. The active risk model is about:

- unauthorized command execution,
- duplicate side effects,
- unsafe direct agent-to-effect execution,
- improper handling of external outcome classification.

Please keep reports focused on the project’s defined control-plane and execution-boundary behavior.

## Notes on maturity

This repository is not presented as production-certified or enterprise-hardened. Security findings should be evaluated against the project’s stated research-stage status and owner-frozen architecture.
