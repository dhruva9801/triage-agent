from __future__ import annotations

import json
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from moto import mock_aws

from tests.conftest import VALID_ULID
from triage.aws import sqs_client
from triage.worker.local import poll_once

if TYPE_CHECKING:
    from mypy_boto3_sqs.client import SQSClient


@pytest.fixture
def sqs() -> Iterator[SQSClient]:
    with mock_aws():
        yield sqs_client("us-east-1")


def _visible_count(sqs: SQSClient, queue_url: str) -> int:
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"]
    )
    return int(attrs["Attributes"]["ApproximateNumberOfMessages"])


def _not_visible_count(sqs: SQSClient, queue_url: str) -> int:
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessagesNotVisible"]
    )
    return int(attrs["Attributes"]["ApproximateNumberOfMessagesNotVisible"])


def test_successful_message_is_deleted(sqs: SQSClient) -> None:
    queue_url = sqs.create_queue(QueueName="triage-work")["QueueUrl"]
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({"user_sub": "u", "posting_id": VALID_ULID}),
    )

    assert poll_once(sqs, queue_url, wait_seconds=0) == 1
    assert _visible_count(sqs, queue_url) == 0
    assert _not_visible_count(sqs, queue_url) == 0


def test_failed_message_is_left_for_redelivery(sqs: SQSClient) -> None:
    queue_url = sqs.create_queue(QueueName="triage-work")["QueueUrl"]
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"bad": True}))

    assert poll_once(sqs, queue_url, wait_seconds=0) == 1
    # Not deleted: in flight now, visible again after the visibility timeout.
    assert _not_visible_count(sqs, queue_url) == 1


def test_empty_queue_returns_zero(sqs: SQSClient) -> None:
    queue_url = sqs.create_queue(QueueName="triage-work")["QueueUrl"]
    assert poll_once(sqs, queue_url, wait_seconds=0) == 0
