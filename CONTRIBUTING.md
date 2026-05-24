# Contributing to persona-hub

Thanks for your interest in contributing.

persona-hub is at **Phase 0** (architecture design). The project is not yet ready for general code contributions, but **design feedback is welcome and high-value right now**.

## Code of Conduct

By participating, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## How to contribute right now (Phase 0)

The most useful contributions in this phase:

1. **Design feedback on [ARCHITECTURE.md](./ARCHITECTURE.md)** — open an Issue with the `design` label.
2. **Security model review** — see [SECURITY.md](./SECURITY.md) and [Issue #1](https://github.com/kenimo49/persona-hub/issues/1). Threat model gaps and attack scenarios are especially welcome.
3. **Profile pack proposals** — sketch a 5-question quiz for a domain you care about (coffee, music, books, productivity styles, etc.) and open an Issue.

## How to contribute later (Phase 1+)

Once `@persona-hub/core` ships and the monorepo is set up:

- **Bug fixes**: open an Issue first, then send a PR.
- **New features**: discuss in an Issue before sending a PR for non-trivial work.
- **Profile packs**: anyone can publish a pack to the `@persona-hub/profiles/*` namespace if it meets the standards below.

## Profile pack contribution standards

Profile packs (`@persona-hub/profiles/*`) are the most natural extension point. To accept a pack into the official namespace, it must:

- **Be evidence-based, not fortune-telling.** Each type description should ground itself in an observable mechanism (olfactory adaptation, learning preferences, working memory, etc.), not vague archetypes.
- **Be licensed Apache 2.0 (or a compatible permissive license).**
- **Not infringe trademarks.** Don't call your pack "MBTI for coffee" or "DiSC for music." Use generic descriptive names.
- **Include tests** using `@persona-hub/core` that verify deterministic scoring.
- **Document the source of any items.** If you adapted public-domain item pools (e.g., IPIP), credit them.

## Development setup

Coming in Phase 1. Tracked in [Issue #2: monorepo setup](https://github.com/kenimo49/persona-hub/issues/2).

## Commit and PR conventions

- Conventional Commits style preferred: `feat:`, `fix:`, `docs:`, `chore:`, etc.
- Keep PRs focused. One concern per PR.
- Reference relevant Issues in the PR body.

## License

By contributing, you agree that your contributions will be licensed under the **Apache License 2.0**.
