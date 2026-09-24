"""Deterministic, advisory-only evaluation of entity obligations and action intents."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any


class InvalidCase(ValueError):
    """An input cannot be evaluated safely."""


def _day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise InvalidCase(f"{field} must be an ISO date") from exc


def _objects(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise InvalidCase(f"{field} must be a list of objects")
    return value


def _unique(items: list[dict[str, Any]], field: str) -> None:
    ids = [item.get("id") for item in items]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise InvalidCase(f"{field} requires unique nonempty ids")


def _digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise InvalidCase("case and pack must contain finite JSON values") from exc
    return hashlib.sha256(raw).hexdigest()


def evaluate(case: dict[str, Any], pack: dict[str, Any], as_of: str) -> dict[str, Any]:
    """Evaluate a synthetic case without executing or authenticating external actions."""
    if not isinstance(case, dict) or not isinstance(pack, dict):
        raise InvalidCase("case and pack must be objects")
    today = _day(as_of, "as_of")
    entity = case.get("entity")
    if not isinstance(entity, dict) or not isinstance(entity.get("id"), str) or not entity["id"].strip():
        raise InvalidCase("entity.id is required")
    if entity.get("jurisdiction") != pack.get("jurisdiction"):
        raise InvalidCase("entity jurisdiction and pack jurisdiction differ")
    if pack.get("status") != "SYNTHETIC_REFERENCE":
        raise InvalidCase("only SYNTHETIC_REFERENCE packs are accepted by this release")
    if not isinstance(pack.get("version"), str) or not pack["version"].strip():
        raise InvalidCase("pack.version is required")
    if today < _day(pack["effective_from"], "pack.effective_from"):
        raise InvalidCase("pack is not yet effective")
    events = _objects(case.get("events", []), "events")
    evidence = _objects(case.get("evidence", []), "evidence")
    grants = _objects(case.get("grants", []), "grants")
    approvals = _objects(case.get("approvals", []), "approvals")
    intents = _objects(case.get("intents", []), "intents")
    rules = _objects(pack.get("obligations", []), "pack.obligations")
    for name, items in (("events", events), ("evidence", evidence), ("grants", grants),
                        ("approvals", approvals), ("intents", intents), ("pack.obligations", rules)):
        _unique(items, name)
    event_by_id = {item["id"]: item for item in events}
    if any(event.get("entity_id") != entity["id"] for event in events):
        raise InvalidCase("all events must belong to entity.id")
    if any(item.get("event_id") not in event_by_id for item in evidence):
        raise InvalidCase("evidence must reference an existing event")
    rule_by_id = {item["id"]: item for item in rules}
    if any(item.get("obligation_id") not in rule_by_id for item in evidence):
        raise InvalidCase("evidence must reference an existing obligation rule")
    if any(event_by_id[item["event_id"]].get("type") != rule_by_id[item["obligation_id"]].get("trigger")
           for item in evidence):
        raise InvalidCase("evidence event must match its obligation trigger")
    intent_by_id = {item["id"]: item for item in intents}
    if any(item.get("intent_id") not in intent_by_id for item in approvals):
        raise InvalidCase("approval must reference an existing intent")
    for grant in grants:
        if grant.get("entity_id") != entity["id"] or not isinstance(grant.get("principal_id"), str) or not grant["principal_id"].strip():
            raise InvalidCase("grant requires an entity-bound principal")
        _day(grant.get("expires_at"), f"grants.{grant['id']}.expires_at")
        if not isinstance(grant.get("actions"), list) or any(not isinstance(x, str) for x in grant["actions"]):
            raise InvalidCase("grant actions must be a list of strings")
    for approval in approvals:
        if approval.get("entity_id") != entity["id"] or not isinstance(approval.get("actor_id"), str) or not approval["actor_id"].strip():
            raise InvalidCase("approval requires an entity-bound actor")
        if approval.get("decision") not in {"approve", "reject"}:
            raise InvalidCase("approval decision must be approve or reject")

    obligations = []
    for rule in rules:
        if not isinstance(rule.get("trigger"), str) or not rule["trigger"].strip() or type(rule.get("due_days")) is not int or rule["due_days"] < 0:
            raise InvalidCase("obligation rules require trigger and nonnegative due_days")
        if not isinstance(rule.get("source_url"), str) or not rule["source_url"].startswith("https://"):
            raise InvalidCase("obligation rules require an https source_url")
        for event in events:
            if event.get("type") != rule["trigger"]:
                continue
            occurred = _day(event.get("occurred_at"), f"events.{event['id']}.occurred_at")
            if occurred > today:
                raise InvalidCase("future events cannot create current obligations")
            due = occurred + timedelta(days=rule["due_days"])
            matches = [item for item in evidence if item.get("obligation_id") == rule["id"]
                       and item.get("event_id") == event["id"]]
            verified = [item for item in matches if item.get("status") == "externally_verified"
                        and item.get("source_kind") in {"provider_attestation", "registry_record"}]
            # A reported artifact cannot suppress an overdue flag without trusted authentication.
            status = "overdue" if today > due else "open"
            evidence_status = "verification_claimed" if verified else ("reported" if matches else "missing")
            obligations.append({"id": f"{rule['id']}:{event['id']}", "rule_id": rule["id"],
                                "event_id": event["id"], "due_at": due.isoformat(), "status": status,
                                "days_until_due": (due - today).days,
                                "evidence_status": evidence_status,
                                "source_url": rule["source_url"], "evidence_ids": [x["id"] for x in matches]})

    decisions = []
    for intent in intents:
        actor, action = intent.get("actor_id"), intent.get("action")
        if not isinstance(actor, str) or not isinstance(action, str):
            raise InvalidCase("intents require actor_id and action")
        valid_grants = [g for g in grants if g.get("principal_id") == actor
                        and g.get("entity_id") == entity["id"] and action in g.get("actions", [])
                        and _day(g.get("expires_at"), f"grants.{g['id']}.expires_at") >= today]
        independent_approval = [a for a in approvals if a.get("intent_id") == intent["id"]
                                and a.get("decision") == "approve" and a.get("actor_id") != actor
                                and a.get("entity_id") == entity["id"]]
        explicit_rejection = any(a.get("intent_id") == intent["id"] and a.get("decision") == "reject"
                                 for a in approvals)
        reasons = []
        if not valid_grants:
            reasons.append("no_active_scoped_grant")
        if not independent_approval:
            reasons.append("independent_approval_missing")
        if explicit_rejection:
            reasons.append("explicit_rejection_present")
        decisions.append({"intent_id": intent["id"], "decision": "reviewable" if not reasons else "deny",
                          "reasons": reasons, "authority": "REFERENCE_ONLY_NOT_AUTHENTICATED"})

    summary = {"obligations_total": len(obligations),
               "overdue": sum(item["status"] == "overdue" for item in obligations),
               "evidence_missing": sum(item["evidence_status"] == "missing" for item in obligations),
               "intents_denied": sum(item["decision"] == "deny" for item in decisions)}
    core = {"schema_version": "0.2", "entity_id": entity["id"], "jurisdiction": entity["jurisdiction"],
            "as_of": today.isoformat(), "pack_version": pack.get("version"),
            "pack_status": pack["status"], "obligations": obligations, "decisions": decisions,
            "summary": summary,
            "limitations": ["Synthetic rules are not legal advice or a filing schedule.",
                            "Evidence source identity, grants, and approvals are not authenticated.",
                            "No external action or filing is executed."]}
    return {**core, "input_digest": _digest({"case": case, "pack": pack}), "receipt_digest": _digest(core)}


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise InvalidCase(f"{path} must contain an object")
    return value
