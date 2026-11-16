"""Typed boto3 client factories.

boto3 picks the client type from a string argument, which strict type checking
cannot fully see through. Creating clients here keeps that one suppression in
one place instead of scattered across the codebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_sqs.client import SQSClient


def sqs_client(region: str, endpoint_url: str | None = None) -> SQSClient:
    return boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "sqs", region_name=region, endpoint_url=endpoint_url
    )
