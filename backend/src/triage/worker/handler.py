"""Worker Lambda: consumes the SQS work queue.

Each record is validated and processed on its own, and failures are reported
per message, so one bad posting never fails its neighbours.
"""

from __future__ import annotations

from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from triage.core.messages import WorkMessage

logger = Logger(service="triage-worker")


def process_message(message: WorkMessage) -> None:
    """Do the work for one posting. For now this only logs the message."""
    logger.info(
        "received work message",
        extra={"posting_id": message.posting_id, "user_sub": message.user_sub},
    )


def process_records(records: list[dict[str, Any]]) -> list[str]:
    """Process SQS records and return the message IDs that failed.

    Shared by the Lambda handler and the local poller, so both run the same
    code path.

    Malformed messages are reported as failures rather than dropped. They will
    never succeed, but dropping them destroys the evidence. After 3 receives SQS
    moves them to the DLQ, which fires the alarm. Fail loudly.
    """
    failed: list[str] = []
    for record in records:
        message_id: str = record["messageId"]
        try:
            message = WorkMessage.model_validate_json(record["body"])
        except ValidationError:
            logger.exception("malformed work message", extra={"message_id": message_id})
            failed.append(message_id)
            continue
        try:
            process_message(message)
        except Exception:
            # Broad on purpose: any failure for one posting must be reported
            # for that message only, never crash the whole batch.
            logger.exception(
                "failed to process work message",
                extra={"message_id": message_id, "posting_id": message.posting_id},
            )
            failed.append(message_id)
    return failed


@logger.inject_lambda_context
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, list[dict[str, str]]]:
    """Lambda entry point.

    Returns the partial-batch-failure shape. With batch size 1 this matters
    little today, but it keeps the handler correct if batch size ever changes.
    Requires `function_response_types = ["ReportBatchItemFailures"]` on the
    event source mapping, which Terraform sets.
    """
    failed = process_records(event.get("Records", []))
    return {"batchItemFailures": [{"itemIdentifier": message_id} for message_id in failed]}
