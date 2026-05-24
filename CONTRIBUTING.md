# Contributing to persona-hub

Thanks for your interest in contributing.

persona-hub is at **Phase 1** (MVP shipped). `@persona-hub/core`, the first profile pack (`fragrance.v1`), the FastAPI Persistence API, and the BigFive aggregation engine are merged and tested on `main`. Code contributions are now in scope.

## Code of Conduct

By participating, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## How to contribute

The most useful contributions right now:

1. **Bug fixes** — open an Issue first if it's non-trivial, then send a PR.
2. **Profile packs** — anyone can publish a pack under `@persona-hub/profiles/*` if it meets the standards below.
3. **Design feedback on [ARCHITECTURE.md](./ARCHITECTURE.md)** — open an Issue with the `design` label. The cross-source handoff flow and aggregation semantics are still evolving pre-1.0.
4. **Security model review** — see [SECURITY.md](./SECURITY.md) and [Issue #1](https://github.com/kenimo49/persona-hub/issues/1). Threat model gaps and attack scenarios are welcome.

For new features, please discuss in an Issue before sending a PR for non-trivial work.

## Local development

### Prerequisites

- Node 20 + pnpm 9 (TypeScript packages)
- Python 3.12 + [uv](https://github.com/astral-sh/uv) (FastAPI service)

### TypeScript packages (`packages/core`, `packages/profiles`)

```bash
pnpm install
pnpm -r typecheck
pnpm -r test
pnpm -r build
```

### Python API (`apps/api`)

```bash
cd apps/api
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check .
mypy app
pytest
```

CI runs all of the above on every PR. Keep tests passing locally before pushing.

## Profile pack contribution standards

Profile packs (`@persona-hub/profiles/*`) are the most natural extension point. To accept a pack into the official namespace, it must:

- **Be evidence-based, not fortune-telling.** Each type description should ground itself in an observable mechanism (olfactory adaptation, learning preferences, working memory, etc.), not vague archetypes.
- **Be licensed Apache 2.0 (or a compatible permissive license).**
- **Not infringe trademarks.** Don't call your pack "MBTI for coffee" or "DiSC for music." Use generic descriptive names.
- **Include tests** using `@persona-hub/core` that verify deterministic scoring.
- **Document the source of any items.** If you adapted public-domain item pools (e.g., IPIP), credit them.

## Commit and PR conventions

- Conventional Commits style preferred: `feat:`, `fix:`, `docs:`, `chore:`, etc.
- Keep PRs focused. One concern per PR.
- Reference relevant Issues in the PR body.

## License

By contributing, you agree that your contributions will be licensed under the **Apache License 2.0**.
