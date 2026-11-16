from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# Tests must never reach real AWS. Fake credentials make any accidental real
# call fail authentication instead of succeeding against your account.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")

VALID_ULID = "01J9Z3K8Q5V7X2M4N6P8R0T2W4"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Settings are cached per process; reset around each test."""
    from triage.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
