# persona-hub API

The persistence and aggregation API for [persona-hub](https://github.com/kenimo49/persona-hub). Optional — clients can use `@persona-hub/core` standalone without this service.

**Status**: scaffold with a `/health` endpoint only. Real endpoints (`POST /personas`, `POST /personas/:id/signals`, `GET /personas/:id`, `GET /personas/:id/aggregate`) land in [Issue #5](https://github.com/kenimo49/persona-hub/issues/5).

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) recommended (or use plain `pip`)

## Development

```bash
cd apps/api

# with uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# or with pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload
```

Then visit http://localhost:8000/health.

## Test

```bash
pytest
```

## Lint and type check

```bash
ruff check .
mypy app
```

## License

Apache-2.0. See repository [LICENSE](../../LICENSE).
