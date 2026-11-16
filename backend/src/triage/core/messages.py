"""Contracts for messages passed between components."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Crockford base32, 26 characters: the ULID format used for posting IDs.
ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"


class WorkMessage(BaseModel):
    """Body of one work-queue message.

    IDs only, never posting text. SQS caps messages at 256 KB, and keeping
    content in S3/DynamoDB means there is exactly one copy to trust.
    `extra="forbid"` rejects unexpected fields instead of silently ignoring them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_sub: str = Field(min_length=1, max_length=128)
    posting_id: str = Field(pattern=ULID_PATTERN)
