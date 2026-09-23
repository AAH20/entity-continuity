"""Recompute a synthetic Entity Continuity receipt from its exact local inputs."""

from __future__ import annotations

import json
from typing import Any

from .engine import InvalidCase, evaluate


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def verify(case: dict[str, Any], pack: dict[str, Any], as_of: str,
           receipt: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise InvalidCase("receipt must be an object")
    expected = evaluate(case, pack, as_of)
    try:
        equal = _canonical(receipt) == _canonical(expected)
    except (TypeError, ValueError) as exc:
        raise InvalidCase("receipt cannot be canonicalized") from exc
    if not equal:
        raise InvalidCase("receipt differs from recomputed case and pack")
    return {"valid": True,
            "scope": "EXACT_LOCAL_SYNTHETIC_RECOMPUTATION_ONLY_NOT_SOURCE_OR_IDENTITY_AUTHENTICATION",
            "entity_id": expected["entity_id"], "receipt_digest": expected["receipt_digest"]}
