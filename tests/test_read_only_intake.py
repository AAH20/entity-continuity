import copy
import tempfile
import unittest
from pathlib import Path

from entity_continuity.engine import InvalidCase, read_json_document
from entity_continuity.read_only_intake import evaluate_intake, verify_intake


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def source_fixture():
    manifest, _ = read_json_document(EXAMPLES / "synthetic-read-only-intake-manifest.json")
    case, case_digest = read_json_document(EXAMPLES / "egypt-to-us-synthetic-case.json")
    pack, pack_digest = read_json_document(EXAMPLES / "us-de-synthetic-pack.json")
    return manifest, case, pack, case_digest, pack_digest


class StrictSourceTests(unittest.TestCase):
    def test_duplicate_keys_nonfinite_and_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            for content, pattern in ((b'{"a":1,"a":2}', "duplicate JSON key"),
                                     (b'{"value":NaN}', "non-finite JSON value")):
                source.write_bytes(content)
                with self.assertRaisesRegex(InvalidCase, pattern):
                    read_json_document(source)
            source.write_bytes(b'{"long":"' + b'a' * 100 + b'"}')
            with self.assertRaisesRegex(InvalidCase, "input limit"):
                read_json_document(source, max_bytes=20)

    def test_exact_raw_bytes_digest_changes_with_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            source.write_text('{"a":1}', encoding="utf-8")
            first, first_digest = read_json_document(source)
            source.write_text('{ "a": 1 }', encoding="utf-8")
            second, second_digest = read_json_document(source)
            self.assertEqual(first, second)
            self.assertNotEqual(first_digest, second_digest)


class ReadOnlyIntakeTests(unittest.TestCase):
    def test_exact_manifest_replay_and_no_authority_claim(self):
        manifest, case, pack, case_digest, pack_digest = source_fixture()
        record = evaluate_intake(manifest, case, pack, "2026-09-23", case_digest, pack_digest)
        self.assertEqual(record["workspace_id"], "demo-workspace")
        self.assertEqual(record["source_counts"], {"events": 2, "evidence": 1, "rules": 2})
        self.assertEqual(record["receipt"]["summary"]["obligations_total"], 2)
        self.assertTrue(verify_intake(manifest, case, pack, "2026-09-23",
                                      case_digest, pack_digest, record)["valid"])
        self.assertIn("not authenticated consent", record["limitations"][0])

    def test_changed_source_expired_scope_and_wrong_workspace_fail(self):
        manifest, case, pack, case_digest, pack_digest = source_fixture()
        with self.assertRaisesRegex(InvalidCase, "source bytes differ"):
            evaluate_intake(manifest, case, pack, "2026-09-23", "0" * 64, pack_digest)
        with self.assertRaisesRegex(InvalidCase, "outside the declared scope"):
            evaluate_intake(manifest, case, pack, "2026-11-01", case_digest, pack_digest)
        altered = copy.deepcopy(manifest)
        altered["entity_id"] = "other-entity"
        with self.assertRaisesRegex(InvalidCase, "differs from the manifest"):
            evaluate_intake(altered, case, pack, "2026-09-23", case_digest, pack_digest)
        altered = copy.deepcopy(manifest)
        altered["sources"]["event_count"] = 3
        with self.assertRaisesRegex(InvalidCase, "event_count"):
            evaluate_intake(altered, case, pack, "2026-09-23", case_digest, pack_digest)

    def test_tampered_record_and_non_synthetic_pack_rejected(self):
        manifest, case, pack, case_digest, pack_digest = source_fixture()
        record = evaluate_intake(manifest, case, pack, "2026-09-23", case_digest, pack_digest)
        altered = copy.deepcopy(record)
        altered["workspace_id"] = "other-workspace"
        with self.assertRaisesRegex(InvalidCase, "exact source replay"):
            verify_intake(manifest, case, pack, "2026-09-23", case_digest, pack_digest, altered)
        altered_pack = copy.deepcopy(pack)
        altered_pack["status"] = "PRODUCTION"
        with self.assertRaisesRegex(InvalidCase, "parsed source differs"):
            evaluate_intake(manifest, case, altered_pack, "2026-09-23", case_digest, pack_digest)


if __name__ == "__main__":
    unittest.main()
