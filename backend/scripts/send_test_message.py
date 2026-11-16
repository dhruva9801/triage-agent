"""Send one work message to the LOCAL queue, to check the worker end to end.

Usage (with `docker compose up` running):
    uv run python scripts/send_test_message.py
    uv run python scripts/send_test_message.py --malformed

This script only ever talks to ElasticMQ on localhost. It is not part of the
deployed image.
"""

from __future__ import annotations

import argparse
import json

import boto3

LOCAL_ENDPOINT = "http://localhost:9324"
LOCAL_QUEUE_URL = f"{LOCAL_ENDPOINT}/000000000000/triage-work"
SAMPLE_POSTING_ID = "01J9Z3K8Q5V7X2M4N6P8R0T2W4"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--malformed",
        action="store_true",
        help="send an invalid body to watch failure handling and the DLQ",
    )
    args = parser.parse_args()

    body = (
        json.dumps({"posting_id": "not-a-ulid"})
        if args.malformed
        else json.dumps({"user_sub": "local-user", "posting_id": SAMPLE_POSTING_ID})
    )
    # ElasticMQ ignores credentials, but boto3 refuses to sign without some.
    sqs = boto3.client(
        "sqs",
        region_name="us-east-1",
        endpoint_url=LOCAL_ENDPOINT,
        aws_access_key_id="local",
        aws_secret_access_key="local",  # noqa: S106 - dummy credential for local ElasticMQ
    )
    sqs.send_message(QueueUrl=LOCAL_QUEUE_URL, MessageBody=body)
    print(f"sent: {body}")


if __name__ == "__main__":
    main()
