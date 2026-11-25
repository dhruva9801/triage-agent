from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date

import pytest
from moto import mock_aws

from triage.aws import dynamodb_table, s3_client
from triage.core.ids import new_ulid
from triage.core.messages import ULID_PATTERN
from triage.core.models import Posting, Source, Status
from triage.store import PostingExistsError, PostingStore

REGION = "us-east-1"
BUCKET = "triage-raw-test"


@pytest.fixture
def store() -> Iterator[PostingStore]:
    with mock_aws():
        table = dynamodb_table("triage", REGION)
        # Same key schema as infra/main/data.tf.
        table.meta.client.create_table(
            TableName="triage",
            BillingMode="PAY_PER_REQUEST",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
        )
        s3 = s3_client(REGION)
        s3.create_bucket(Bucket=BUCKET)
        yield PostingStore(table, s3, BUCKET)


def test_ulids_match_the_message_pattern_and_sort_by_time() -> None:
    earlier, later = new_ulid(now_ms=1_000), new_ulid(now_ms=2_000)
    assert re.fullmatch(ULID_PATTERN, earlier)
    assert earlier < later
    assert new_ulid() != new_ulid()


def test_create_then_get_round_trips(store: PostingStore) -> None:
    posting = Posting.new("user-a", Source.MANUAL)
    store.create(posting)

    assert store.get("user-a", posting.posting_id) == posting


def test_create_never_overwrites(store: PostingStore) -> None:
    posting = Posting.new("user-a", Source.MANUAL)
    store.create(posting)

    with pytest.raises(PostingExistsError):
        store.create(posting.model_copy(update={"status": Status.FAILED}))
    assert store.get("user-a", posting.posting_id) == posting


def test_users_cannot_see_each_others_postings(store: PostingStore) -> None:
    posting = Posting.new("user-a", Source.MANUAL)
    store.create(posting)

    assert store.get("user-b", posting.posting_id) is None
    assert store.list_for_user("user-b") == []


def test_list_returns_only_own_postings_newest_first(store: PostingStore) -> None:
    older = Posting.new("user-a", Source.MANUAL).model_copy(
        update={"posting_id": new_ulid(now_ms=1_000)}
    )
    newer = Posting.new("user-a", Source.GREENHOUSE, url="https://example.com/j/1").model_copy(
        update={"posting_id": new_ulid(now_ms=2_000)}
    )
    for posting in (older, newer, Posting.new("user-b", Source.MANUAL)):
        store.create(posting)

    assert [p.posting_id for p in store.list_for_user("user-a")] == [
        newer.posting_id,
        older.posting_id,
    ]


def test_quota_allows_exactly_the_limit_per_day(store: PostingStore) -> None:
    today, tomorrow = date(2026, 11, 24), date(2026, 11, 25)

    assert [store.consume_quota("user-a", today, limit=2) for _ in range(3)] == [
        True,
        True,
        False,
    ]
    assert store.consume_quota("user-a", tomorrow, limit=2)
    assert store.consume_quota("user-b", today, limit=2)


def test_raw_text_round_trips(store: PostingStore) -> None:
    store.put_raw("user-a", "01J9Z3K8Q5V7X2M4N6P8R0T2W4", "Senior engineer — Python, AWS ✓")

    assert store.get_raw("user-a", "01J9Z3K8Q5V7X2M4N6P8R0T2W4") == (
        "Senior engineer — Python, AWS ✓"
    )
