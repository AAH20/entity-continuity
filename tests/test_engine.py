import copy
import json
import unittest
from pathlib import Path

from entity_continuity.engine import InvalidCase, evaluate
from entity_continuity.verify import verify


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class EntityContinuityTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture("egypt-to-us-synthetic-case.json")
        self.pack = fixture("us-de-synthetic-pack.json")

    def test_replay_and_advisory_boundary(self):
        one = evaluate(self.case, self.pack, "2026-09-23")
        two = evaluate(self.case, self.pack, "2026-09-23")
        self.assertEqual(one, two)
        self.assertEqual([x["status"] for x in one["obligations"]], ["open", "overdue"])
        self.assertEqual(one["obligations"][0]["evidence_status"], "reported")
        self.assertEqual([x["decision"] for x in one["decisions"]], ["reviewable", "deny"])
        self.assertEqual(one["decisions"][0]["authority"], "REFERENCE_ONLY_NOT_AUTHENTICATED")
        self.assertTrue(verify(self.case, self.pack, "2026-09-23", one)["valid"])

    def test_receipt_verifier_rejects_changed_decision_and_source(self):
        receipt = evaluate(self.case, self.pack, "2026-09-23")
        altered = copy.deepcopy(receipt)
        altered["decisions"][0]["decision"] = "authorized"
        with self.assertRaisesRegex(InvalidCase, "differs"):
            verify(self.case, self.pack, "2026-09-23", altered)
        changed_case = copy.deepcopy(self.case)
        changed_case["events"][0]["occurred_at"] = "2026-09-02"
        with self.assertRaisesRegex(InvalidCase, "differs"):
            verify(changed_case, self.pack, "2026-09-23", receipt)

    def test_wrong_jurisdiction_fails_closed(self):
        changed = copy.deepcopy(self.case)
        changed["entity"]["jurisdiction"] = "EG"
        with self.assertRaises(InvalidCase):
            evaluate(changed, self.pack, "2026-09-23")

    def test_self_approval_and_expired_grant_are_denied(self):
        changed = copy.deepcopy(self.case)
        changed["approvals"][0]["actor_id"] = "founder"
        changed["grants"][0]["expires_at"] = "2026-09-22"
        decision = evaluate(changed, self.pack, "2026-09-23")["decisions"][0]
        self.assertEqual(decision["decision"], "deny")
        self.assertEqual(set(decision["reasons"]), {"no_active_scoped_grant", "independent_approval_missing"})

    def test_claimed_verification_is_not_authenticated(self):
        changed = copy.deepcopy(self.case)
        changed["evidence"][0]["status"] = "externally_verified"
        changed["evidence"][0]["source_kind"] = "registry_record"
        obligation = evaluate(changed, self.pack, "2026-09-23")["obligations"][0]
        self.assertEqual(obligation["status"], "open")
        self.assertEqual(obligation["evidence_status"], "verification_claimed")

    def test_duplicate_ids_rejected(self):
        changed = copy.deepcopy(self.case)
        changed["events"].append(copy.deepcopy(changed["events"][0]))
        with self.assertRaises(InvalidCase):
            evaluate(changed, self.pack, "2026-09-23")


if __name__ == "__main__":
    unittest.main()
