"""HTTP API.

`/health` returns the commit SHA baked into the image at build time. The
deploy pipeline's smoke test compares it with the commit it just shipped,
which proves the new code is live rather than merely that something answers.
"""

from __future__ import annotations

from fastapi import FastAPI

from triage.config import get_settings

settings = get_settings()

# Interactive docs only run locally. The deployed API does not publish its
# schema.
_is_local = settings.environment == "local"

app = FastAPI(
    title="Job Posting Triage Agent",
    version="0.1.0",
    docs_url="/docs" if _is_local else None,
    redoc_url=None,
    openapi_url="/openapi.json" if _is_local else None,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Unauthenticated liveness check. Returns the deployed commit SHA."""
    return {"status": "ok", "version": settings.git_sha}
