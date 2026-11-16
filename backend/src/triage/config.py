"""Runtime configuration, read from environment variables.

Nothing environment-specific is hardcoded, so the same image runs under Docker
Compose and on Lambda. Terraform sets these on Lambda; docker-compose.yml sets
them locally.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def running_on_lambda() -> bool:
    """Lambda always sets this variable; nothing else does."""
    return "AWS_LAMBDA_FUNCTION_NAME" in os.environ


@dataclass(frozen=True)
class Settings:
    environment: str
    aws_region: str
    git_sha: str
    work_queue_url: str | None
    # Only set locally, to point boto3 at ElasticMQ instead of real SQS.
    sqs_endpoint_url: str | None


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        environment=os.environ.get("TRIAGE_ENV", "local"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        git_sha=os.environ.get("GIT_SHA", "dev"),
        work_queue_url=os.environ.get("WORK_QUEUE_URL") or None,
        sqs_endpoint_url=os.environ.get("SQS_ENDPOINT_URL") or None,
    )
    _refuse_local_overrides_on_lambda(settings)
    return settings


def _refuse_local_overrides_on_lambda(settings: Settings) -> None:
    """Fail at startup if a local-only override leaks into a deployed function.

    A stray SQS_ENDPOINT_URL on Lambda would silently send work nowhere.
    Misconfiguration should crash loudly at cold start, not degrade quietly
    at 2am.
    """
    if running_on_lambda() and settings.sqs_endpoint_url is not None:
        raise RuntimeError("SQS_ENDPOINT_URL is a local-only setting and must not be set on Lambda")
