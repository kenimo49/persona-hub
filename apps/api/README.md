# persona-hub API

The persistence and aggregation API for [persona-hub](https://github.com/kenimo49/persona-hub). Optional — clients can use `@persona-hub/core` standalone without this service.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/personas` | `X-API-Key` | Create a persona with its first signal. Returns `{ persona_id }`. |
| POST | `/personas/{id}/signals` | `X-API-Key` (with access) **or** `+ Authorization: Bearer <handoff>` | Append a signal from another source service. |
| GET | `/personas/{id}` | Same as above | Return the persona's signals (and the aggregate placeholder). |
| GET | `/personas/{id}/aggregate` | Same as above | Aggregated cross-source estimate. Surfaces a Big Five (OCEAN) estimate when a `bigfive.v1` signal is present (server re-scores from `answers` when available, otherwise trusts the signal's `result`). |
| POST | `/personas/{id}/handoff_token` | `X-API-Key` (with access) | Issue a short-lived signed JWT to share access with another source service. |
| GET | `/health` | none | Liveness probe. |

Once the server is running, the full interactive schema lives at <http://localhost:8000/docs>.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) recommended (or plain `pip`)

## Development

```bash
cd apps/api

uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# Schema: either init the dev SQLite via Alembic ...
alembic upgrade head
# ... or let the lifespan handler create tables on first start (sqlite only).

uvicorn app.main:app --reload
```

Visit <http://localhost:8000/docs> for the OpenAPI UI and <http://localhost:8000/health> for the liveness check.

## Configuration

All settings are loaded from environment variables prefixed with `PH_`. They can also live in a `.env` file in the working directory.

| Variable | Default | Purpose |
|----------|---------|---------|
| `PH_DATABASE_URL` | `sqlite:///./persona_hub.db` | SQLAlchemy URL. Use `postgresql+psycopg://...` in production. |
| `PH_JWT_SECRET` | `change-me-in-production` | Symmetric key for HS256 handoff token signing. **Must be overridden in production** (use a 32+ byte random value). |
| `PH_JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `PH_HANDOFF_TOKEN_TTL_SECONDS` | `300` | Lifetime of handoff tokens. |
| `PH_RATE_LIMIT_DEFAULT` | `100/minute` | Default rate limit per API key (or per IP for anonymous requests). |
| `PH_ENABLE_RATE_LIMIT` | `true` | Set to `false` for tests or local exploration. |

## Test

```bash
pytest
```

Coverage threshold is 80% (enforced via `--cov-fail-under` in `pyproject.toml`).

## Lint and type check

```bash
ruff check .
mypy app
```

## Migrations

This service uses [Alembic](https://alembic.sqlalchemy.org/) for schema migrations.

```bash
# Apply all pending migrations
alembic upgrade head

# Revert to the previous revision
alembic downgrade -1

# Author a new migration (autogenerate from model diffs)
alembic revision --autogenerate -m "describe the change"
```

The initial revision `0001_initial` creates: `source_api_keys`, `personas`, `signals`, `persona_access`, `handoff_jti`.

For SQLite-based local development the FastAPI lifespan handler also calls `Base.metadata.create_all()`, so a fresh checkout can be exercised without first running Alembic. Production deployments must rely on Alembic.

## Auth model

- Each consuming service (kaoriq, mypcrig, …) is provisioned a row in `source_api_keys` containing a SHA-256 hash of its key plus an indexable lookup prefix. The literal key is shown to the operator exactly once at provisioning time.
- `POST /personas` automatically grants the calling key access to the persona it creates (`persona_access` row with `granted_via='creator'`).
- For cross-source flows the originator calls `POST /personas/{id}/handoff_token` to mint a short-lived JWT. The consumer presents that JWT as `Authorization: Bearer …` on their first request alongside their own `X-API-Key`. On success the JTI is marked consumed (single-use) and the consumer's key receives a permanent `persona_access` row.
- Optional whitelist: a key with a non-empty `allowed_profile_ids` list can only write signals whose `profile_id` is on that list.

## Out of scope for this MVP

- **Cross-domain aggregation.** Mapping domain signals (e.g. fragrance `citrus`, PC `minimal-silent`) to Big Five / MBTI estimates is not yet implemented. Today only an existing `bigfive.v1` signal contributes to `big_five_estimate`.
- **Frameworks beyond Big Five.** MBTI, DiSC, Enneagram, and StrengthsFinder scoring lives in the maintainer's private persona-manager but is held back from this OSS repo until the question items are redesigned for unambiguous OSS licensing.
- **Server-side re-evaluation of arbitrary profiles.** Re-scoring at `/aggregate` only applies to `bigfive.v1`; other framework profiles trust the client-supplied `result`.
- **Scoped handoff tokens.** All tokens currently grant read+write. Read-only variants are deferred.

## License

Apache-2.0. See repository [LICENSE](../../LICENSE).
