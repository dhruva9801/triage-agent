"""Persistence for postings: one DynamoDB table plus one S3 bucket.

Single-table layout, every item partitioned by the owner's Cognito `sub`:

    PK = USER#<sub>   SK = POSTING#<ulid>       one posting
    PK = USER#<sub>   SK = QUOTA#<yyyy-mm-dd>   that day's submission counter

Every read and write takes the user's `sub` and builds the key from it, so no
method can reach another tenant's items. Raw posting text lives in S3 under
raw/<sub>/<id>.txt: it can be large, and DynamoDB items cap at 400 KB.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING

from triage.core.models import Posting

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_s3.client import S3Client


class PostingExistsError(Exception):
    """A posting with this ID already exists for this user."""


def _pk(user_sub: str) -> str:
    return f"USER#{user_sub}"


def raw_key(user_sub: str, posting_id: str) -> str:
    return f"raw/{user_sub}/{posting_id}.txt"


class PostingStore:
    def __init__(self, table: Table, s3: S3Client, bucket: str) -> None:
        self._table = table
        self._s3 = s3
        self._bucket = bucket
        self._conditional_failed = table.meta.client.exceptions.ConditionalCheckFailedException

    def create(self, posting: Posting) -> None:
        """Insert a new posting. Never overwrites: a retried request with the
        same ID fails instead of silently resetting the posting's progress."""
        item = {
            "PK": _pk(posting.user_sub),
            "SK": f"POSTING#{posting.posting_id}",
            **posting.model_dump(mode="json", exclude_none=True),
        }
        try:
            self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
        except self._conditional_failed as exc:
            raise PostingExistsError(posting.posting_id) from exc

    def get(self, user_sub: str, posting_id: str) -> Posting | None:
        response = self._table.get_item(Key={"PK": _pk(user_sub), "SK": f"POSTING#{posting_id}"})
        item = response.get("Item")
        return None if item is None else Posting.model_validate(item)

    def list_for_user(self, user_sub: str, limit: int = 50) -> list[Posting]:
        """The user's most recent postings, newest first (ULIDs sort by time)."""
        response = self._table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
            ExpressionAttributeValues={":pk": _pk(user_sub), ":prefix": "POSTING#"},
            ScanIndexForward=False,
            Limit=limit,
        )
        return [Posting.model_validate(item) for item in response.get("Items", [])]

    def consume_quota(self, user_sub: str, day: date, limit: int) -> bool:
        """Count one submission against the user's daily limit.

        One atomic conditional update: two concurrent requests can never both
        take the last slot. Returns False, and counts nothing, when the limit
        is reached. The counter deletes itself via TTL a day after it ends.
        """
        expires = datetime.combine(day + timedelta(days=2), time.min, tzinfo=UTC)
        try:
            self._table.update_item(
                Key={"PK": _pk(user_sub), "SK": f"QUOTA#{day.isoformat()}"},
                UpdateExpression="ADD used :one SET expires_at = :expires",
                ConditionExpression="attribute_not_exists(used) OR used < :limit",
                ExpressionAttributeValues={
                    ":one": 1,
                    ":limit": limit,
                    ":expires": int(expires.timestamp()),
                },
            )
        except self._conditional_failed:
            return False
        return True

    def put_raw(self, user_sub: str, posting_id: str, text: str) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=raw_key(user_sub, posting_id),
            Body=text.encode(),
            ContentType="text/plain; charset=utf-8",
        )

    def get_raw(self, user_sub: str, posting_id: str) -> str:
        response = self._s3.get_object(Bucket=self._bucket, Key=raw_key(user_sub, posting_id))
        return response["Body"].read().decode()
