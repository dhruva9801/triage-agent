"""Local stand-in for Lambda's SQS event source mapping.

Long-polls the local ElasticMQ queue and runs each message through
`process_records`, the same function the Lambda handler uses. Successful
messages are deleted; failed ones are left to reappear after the visibility
timeout, which is exactly what SQS + Lambda does in AWS.

Run with: python -m triage.worker.local
"""

from __future__ import annotations

import signal
import sys
from types import FrameType
from typing import TYPE_CHECKING, Any

from aws_lambda_powertools import Logger

from triage.aws import sqs_client
from triage.config import get_settings, running_on_lambda
from triage.worker.handler import process_records

if TYPE_CHECKING:
    from mypy_boto3_sqs.client import SQSClient

logger = Logger(service="triage-worker-local")

_stop = False


def _request_stop(signum: int, frame: FrameType | None) -> None:
    global _stop
    _stop = True
    logger.info("stop requested; finishing current poll")


def poll_once(sqs: SQSClient, queue_url: str, wait_seconds: int = 20) -> int:
    """Receive at most one message, process it, delete it on success.

    Returns the number of messages received (0 or 1).
    """
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=wait_seconds,
    )
    messages = response.get("Messages", [])
    for msg in messages:
        # The SDK types these as optional. SQS always sets them on received
        # messages, but checking costs nothing and avoids a KeyError surprise.
        message_id = msg.get("MessageId")
        body = msg.get("Body")
        receipt = msg.get("ReceiptHandle")
        if message_id is None or body is None or receipt is None:
            logger.error("received message missing required fields", extra={"message": msg})
            continue
        record: dict[str, Any] = {"messageId": message_id, "body": body}
        if message_id not in process_records([record]):
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
    return len(messages)


def main() -> None:
    if running_on_lambda():
        sys.exit("The local poller must not run on Lambda")
    settings = get_settings()
    if settings.work_queue_url is None:
        sys.exit("WORK_QUEUE_URL is not set")

    sqs = sqs_client(settings.aws_region, settings.sqs_endpoint_url)
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    logger.info("polling", extra={"queue_url": settings.work_queue_url})
    while not _stop:
        poll_once(sqs, settings.work_queue_url)


if __name__ == "__main__":
    main()
