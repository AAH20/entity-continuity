"""Exact-source recomputation for a read-only synthetic intake record."""

import argparse
import json

from .engine import InvalidCase, read_json_document
from .read_only_intake import verify_intake


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an exact synthetic intake record")
    parser.add_argument("manifest")
    parser.add_argument("case")
    parser.add_argument("pack")
    parser.add_argument("record")
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        manifest, _ = read_json_document(args.manifest, max_bytes=16_384)
        case, case_digest = read_json_document(args.case)
        pack, pack_digest = read_json_document(args.pack)
        record, _ = read_json_document(args.record)
        result = verify_intake(manifest, case, pack, args.as_of, case_digest, pack_digest, record)
    except (InvalidCase, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
