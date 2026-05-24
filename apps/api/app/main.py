"""persona-hub persistence API.

Scaffold with a /health endpoint. Real endpoints land in Issue #5.

See: https://github.com/kenimo49/persona-hub/issues/5
"""

from fastapi import FastAPI

app = FastAPI(
    title="persona-hub API",
    description="Persistence and aggregation API for persona-hub.",
    version="0.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
