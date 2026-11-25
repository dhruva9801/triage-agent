"""Posting IDs.

A ULID is 128 bits: a 48-bit millisecond timestamp followed by 80 random bits,
written as 26 Crockford base32 characters. IDs created later sort later, so
DynamoDB returns a user's postings newest-first by sort key alone, with no
extra index. Ten lines here instead of a dependency.
"""

from __future__ import annotations

import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid(now_ms: int | None = None) -> str:
    ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    value = (ms << 80) | secrets.randbits(80)
    chars = [_CROCKFORD[(value >> shift) & 0b11111] for shift in range(125, -1, -5)]
    return "".join(chars)
