# Security Policy

## Supported versions

persona-hub is currently in **Phase 0** (architecture design). No versions are production-ready. Security reports are still welcome — early findings shape the design.

| Phase | Status | Receives security fixes |
|-------|--------|------------------------|
| 0 (design) | Current | Yes (design-level discussion) |
| 1 (MVP) | Planned | Yes |
| Future stable releases | TBD | Yes (latest minor only, initially) |

## Reporting a vulnerability

Please report security vulnerabilities **privately**, not via public Issues.

**Preferred channel**: [GitHub's private vulnerability reporting](https://github.com/kenimo49/persona-hub/security/advisories/new) on this repository.

If GitHub private reporting is unavailable to you, open a regular Issue titled "Security report (private contact requested)" with no details, and a maintainer will reach out with a private channel.

## What to include

- Affected component (SDK / API / profile pack / docs)
- Reproduction steps or proof-of-concept (no live exploitation against third parties, please)
- Impact assessment from your perspective
- Any suggested mitigation

## Disclosure timeline

- **Acknowledgment**: within 5 business days
- **Initial assessment**: within 14 days
- **Coordinated disclosure**: timeline negotiated with reporter, typically 30-90 days from acknowledgment depending on severity and exploit feasibility

## Scope

In-scope:

- The `@persona-hub/core` SDK
- The persistence API (when self-hosted from this repository's code)
- The profile pack format
- Documented attack surfaces in [ARCHITECTURE.md](./ARCHITECTURE.md#security--privacy-model)

Out-of-scope:

- Self-hosted deployments where the operator has misconfigured auth, TLS, or rate limits
- Third-party integrations and forks
- The `kaoriq.com`, `mypcrig.com`, and `legacydram.com` dogfooding sites (report those issues to their respective maintainers)
- Issues in upstream dependencies (report to the dependency directly, then notify us)

## Threat model

See [ARCHITECTURE.md → Security & privacy model](./ARCHITECTURE.md#security--privacy-model) for the current threat model and required defenses. Significant gaps in that model are themselves valid reports.

## Recognition

We will credit reporters in release notes unless you request anonymity. No monetary bounty program exists in Phase 0.
