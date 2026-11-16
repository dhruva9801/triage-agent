from __future__ import annotations

import pytest

from triage.config import get_settings


def test_local_endpoint_override_allowed_off_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.setenv("SQS_ENDPOINT_URL", "http://localhost:9324")

    assert get_settings().sqs_endpoint_url == "http://localhost:9324"


def test_local_endpoint_override_refused_on_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "triage-worker")
    monkeypatch.setenv("SQS_ENDPOINT_URL", "http://localhost:9324")

    with pytest.raises(RuntimeError, match="local-only"):
        get_settings()
