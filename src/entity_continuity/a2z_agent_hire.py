"""Offline, human-reviewed handoff to the A2Z Agent Hire local job contract."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .engine import InvalidCase, evaluate
from .verify import verify


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_handoff(case: dict[str, Any], pack: dict[str, Any], as_of: str,
                  receipt: dict[str, Any]) -> dict[str, Any]:
    """Create review-only job drafts; no network call, job creation or provider authority."""
    verify(case, pack, as_of, receipt)
    expected = evaluate(case, pack, as_of)
    jobs = []
    for obligation in expected["obligations"]:
        source = {"entity_id": expected["entity_id"], "obligation_id": obligation["id"],
                  "receipt_digest": expected["receipt_digest"]}
        job_id = "JOB-EC-" + _digest(source)[:16].upper()
        title = f"Review entity obligation {obligation['id']}"
        objective = ("Prepare an evidence-gap assessment and recommended next steps for human review. "
                     "Do not file, contact a registry, make legal conclusions, or treat this task as authorization. "
                     f"Reference obligation {obligation['id']} due {obligation['due_at']} "
                     f"with {obligation['evidence_status']} evidence.")
        job = {
            "id": job_id,
            "title": title,
            "objective": objective,
            "budget_usd": 0,
            "customer_price_usd": 0,
            "acceptance_criteria": [
                {"id": "SOURCE_RECONCILED", "description": "Reviewer checked the exact source receipt and obligation ID", "required": True},
                {"id": "EVIDENCE_GAPS", "description": "Missing or unverified evidence is explicitly identified", "required": True},
                {"id": "HUMAN_ACCEPTANCE", "description": "Named human accepts the review deliverable", "required": True},
            ],
            "worker_policy": {"allowed_worker_types": ["human"], "requires_independent_verifier": True},
            "evidence_class": "SYNTHETIC",
        }
        jobs.append({"source": {**source, "jurisdiction": expected["jurisdiction"],
                                "rule_id": obligation["rule_id"], "event_id": obligation["event_id"],
                                "due_at": obligation["due_at"], "status": obligation["status"],
                                "evidence_status": obligation["evidence_status"]},
                     "a2z_job": job})
    bundle = {"schema_version": "entity-continuity.a2z-agent-hire.v1",
              "scope": "SYNTHETIC_REVIEW_DRAFTS_ONLY_NO_EXTERNAL_ACTION",
              "as_of": as_of, "source_receipt_digest": expected["receipt_digest"],
              "jobs": jobs}
    return {**bundle, "bundle_digest": _digest(bundle)}


def verify_handoff(case: dict[str, Any], pack: dict[str, Any], as_of: str,
                   receipt: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    """Verify exact local source inputs and every output field by recomputation."""
    if not isinstance(handoff, dict):
        raise InvalidCase("handoff must be an object")
    expected = build_handoff(case, pack, as_of, receipt)
    if _digest(handoff) != _digest(expected):
        raise InvalidCase("handoff differs from recomputed source and receipt")
    return {"valid": True, "scope": expected["scope"], "bundle_digest": expected["bundle_digest"]}
