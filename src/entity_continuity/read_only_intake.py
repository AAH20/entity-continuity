"""Strict, local, synthetic-only intake with a declared scope and source manifest."""

from __future__ import annotations

import re
from typing import Any

from .engine import InvalidCase, _day, _digest, evaluate


SCHEMA = "entity-continuity.read-only-intake.v1"
SCOPE = "SYNTHETIC_READ_ONLY_EVALUATION_NOT_AUTHENTICATED_CONSENT"


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def evaluate_intake(manifest: dict[str, Any], case: dict[str, Any], pack: dict[str, Any],
                    as_of: str, case_sha256: str, pack_sha256: str) -> dict[str, Any]:
    """Evaluate only exact, declared synthetic sources; never authenticate consent."""
    if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version", "scope", "workspace_id", "entity_id", "jurisdiction",
            "declared_scope", "sources"}:
        raise InvalidCase("intake manifest has an unsupported shape")
    if manifest["schema_version"] != SCHEMA or manifest["scope"] != SCOPE:
        raise InvalidCase("intake manifest must be synthetic and read-only")
    if any(not _text(manifest[key]) for key in ("workspace_id", "entity_id", "jurisdiction")):
        raise InvalidCase("intake workspace, entity and jurisdiction are required")
    declared = manifest["declared_scope"]
    if not isinstance(declared, dict) or set(declared) != {
            "reference", "purpose", "valid_from", "valid_until"}:
        raise InvalidCase("declared_scope has an unsupported shape")
    if not _text(declared["reference"]) or declared["purpose"] != "READ_ONLY_OBLIGATION_REVIEW":
        raise InvalidCase("intake requires a declared read-only review purpose")
    today = _day(as_of, "as_of")
    if not _day(declared["valid_from"], "declared_scope.valid_from") <= today <= _day(
            declared["valid_until"], "declared_scope.valid_until"):
        raise InvalidCase("intake evaluation date is outside the declared scope")
    sources = manifest["sources"]
    if not isinstance(sources, dict) or set(sources) != {
            "case_sha256", "pack_sha256", "case_json_digest", "pack_json_digest",
            "event_count", "evidence_count", "rule_count"}:
        raise InvalidCase("intake source inventory has an unsupported shape")
    if not all(_hash(value) for value in (sources["case_sha256"], sources["pack_sha256"],
                                          sources["case_json_digest"], sources["pack_json_digest"],
                                          case_sha256, pack_sha256)):
        raise InvalidCase("intake source digests must be lowercase SHA-256")
    if sources["case_sha256"] != case_sha256 or sources["pack_sha256"] != pack_sha256:
        raise InvalidCase("intake source bytes differ from the declared manifest")
    if not isinstance(case, dict) or not isinstance(pack, dict):
        raise InvalidCase("intake case and pack must be objects")
    if _digest(case) != sources["case_json_digest"] or _digest(pack) != sources["pack_json_digest"]:
        raise InvalidCase("intake parsed source differs from the declared manifest")
    entity = case.get("entity")
    if (not isinstance(entity, dict) or entity.get("id") != manifest["entity_id"] or
            entity.get("jurisdiction") != manifest["jurisdiction"] or
            pack.get("jurisdiction") != manifest["jurisdiction"]):
        raise InvalidCase("intake entity or jurisdiction differs from the manifest")
    for field, records in (("event_count", case.get("events")),
                           ("evidence_count", case.get("evidence")),
                           ("rule_count", pack.get("obligations"))):
        if (not isinstance(records, list) or type(sources[field]) is not int or
                sources[field] < 0 or len(records) != sources[field]):
            raise InvalidCase(f"intake {field} does not reconcile")
    receipt = evaluate(case, pack, as_of)
    core = {"schema_version": SCHEMA, "scope": SCOPE,
            "workspace_id": manifest["workspace_id"], "entity_id": receipt["entity_id"],
            "jurisdiction": receipt["jurisdiction"], "as_of": receipt["as_of"],
            "declared_scope_reference": declared["reference"],
            "manifest_digest": _digest(manifest),
            "source_sha256": {"case": case_sha256, "pack": pack_sha256},
            "source_counts": {"events": sources["event_count"],
                              "evidence": sources["evidence_count"], "rules": sources["rule_count"]},
            "receipt": receipt,
            "limitations": ["The declared scope is not authenticated consent.",
                            "Only a synthetic rule pack is evaluated; no real filing calendar is asserted.",
                            "Workspace ID is a namespace, not access control or tenant isolation."]}
    return {**core, "record_digest": _digest(core)}


def verify_intake(manifest: dict[str, Any], case: dict[str, Any], pack: dict[str, Any],
                  as_of: str, case_sha256: str, pack_sha256: str,
                  record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise InvalidCase("intake record must be an object")
    expected = evaluate_intake(manifest, case, pack, as_of, case_sha256, pack_sha256)
    if _digest(record) != _digest(expected):
        raise InvalidCase("intake record differs from exact source replay")
    return {"valid": True, "scope": SCOPE, "record_digest": expected["record_digest"]}
