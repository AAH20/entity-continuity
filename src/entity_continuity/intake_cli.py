"""Read-only synthetic source-manifest evaluation."""

import argparse
import json
import sys

from .engine import InvalidCase, read_json_document
from .read_only_intake import evaluate_intake


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a declared synthetic read-only intake")
    parser.add_argument("manifest")
    parser.add_argument("case")
    parser.add_argument("pack")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", help="Write intake record here; defaults to stdout")
    args = parser.parse_args()
    try:
        manifest, _ = read_json_document(args.manifest, max_bytes=16_384)
        case, case_digest = read_json_document(args.case)
        pack, pack_digest = read_json_document(args.pack)
        record = evaluate_intake(manifest, case, pack, args.as_of, case_digest, pack_digest)
    except (InvalidCase, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    encoded = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(encoded)
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
