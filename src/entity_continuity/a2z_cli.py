"""Emit a deterministic A2Z Agent Hire review-job handoff bundle."""

import argparse
import json
import sys

from .a2z_agent_hire import build_handoff
from .engine import InvalidCase, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Export synthetic review jobs for A2Z Agent Hire")
    parser.add_argument("case")
    parser.add_argument("pack")
    parser.add_argument("receipt")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", help="Output JSON file; defaults to stdout")
    args = parser.parse_args()
    try:
        bundle = build_handoff(load_json(args.case), load_json(args.pack), args.as_of,
                               load_json(args.receipt))
    except (InvalidCase, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    encoded = json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(encoded)
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
