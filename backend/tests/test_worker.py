from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext

from tests.conftest import VALID_ULID
from triage.core.messages import WorkMessage
from triage.worker import handler as worker


def _record(message_id: str, body: object) -> dict[str, Any]:
    return {"messageId": message_id, "body": json.dumps(body)}


def _valid_body() -> dict[str, str]:
    return {"user_sub": "user-1", "posting_id": VALID_ULID}


@dataclass
class FakeContext:
    function_name: str = "triage-worker"
    memory_limit_in_mb: int = 512
    invoked_function_arn: str = "arn:aws:lambda:us-east-1:000000000000:function:triage-worker"
    aws_request_id: str = "req-1"


def test_valid_message_succeeds() -> None:
    assert worker.process_records([_record("m1", _valid_body())]) == []


@pytest.mark.parametrize(
    "body",
    [
        {"posting_id": VALID_ULID},  # missing user_sub
        {"user_sub": "u", "posting_id": "not-a-ulid"},  # bad ID format
        {**_valid_body(), "text": "posting text must never be in a message"},  # extra field
    ],
)
def test_malformed_message_is_reported_not_dropped(body: dict[str, str]) -> None:
    assert worker.process_records([_record("m1", body)]) == ["m1"]


def test_processing_error_fails_only_that_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode_on_m2(message: WorkMessage) -> None:
        if message.user_sub == "boom":
            raise RuntimeError("simulated failure")

    monkeypatch.setattr(worker, "process_message", explode_on_m2)
    records = [
        _record("m1", _valid_body()),
        _record("m2", {"user_sub": "boom", "posting_id": VALID_ULID}),
        _record("m3", _valid_body()),
    ]

    assert worker.process_records(records) == ["m2"]


def test_handler_returns_partial_batch_failure_shape() -> None:
    event = {"Records": [_record("m1", _valid_body()), _record("m2", {"bad": True})]}

    result = worker.handler(event, cast(LambdaContext, FakeContext()))

    assert result == {"batchItemFailures": [{"itemIdentifier": "m2"}]}
