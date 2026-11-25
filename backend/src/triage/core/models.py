"""Domain models: what a posting is, independent of where it is stored."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from triage.core.ids import new_ulid
from triage.core.messages import ULID_PATTERN


class Source(StrEnum):
    MANUAL = "manual"
    GREENHOUSE = "greenhouse"


class Status(StrEnum):
    """Pipeline stages. ANALYZED and FAILED are terminal."""

    PENDING = "PENDING"
    FETCHED = "FETCHED"
    EXTRACTED = "EXTRACTED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class Posting(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_sub: str = Field(min_length=1, max_length=128)
    posting_id: str = Field(pattern=ULID_PATTERN)
    source: Source
    url: str | None = None
    status: Status = Status.PENDING
    attempt_count: int = 0
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, user_sub: str, source: Source, url: str | None = None) -> Posting:
        now = datetime.now(UTC)
        return cls(
            user_sub=user_sub,
            posting_id=new_ulid(),
            source=source,
            url=url,
            created_at=now,
            updated_at=now,
        )
