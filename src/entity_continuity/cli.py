"""Command-line entry point for the offline reference evaluation."""

import argparse
import json
import sys

from .engine import InvalidCase, evaluate, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate an advisory-only synthetic entity case")
    parser.add_argument("case")
    parser.add_argument("pack")
    parser.add_argument("--as-of", required=True, help="ISO date, e.g. 2026-09-23")
    parser.add_argument("--output", help="Write receipt to this file; defaults to stdout")
    args = parser.parse_args()
    try:
        result = evaluate(load_json(args.case), load_json(args.pack), args.as_of)
    except (InvalidCase, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(encoded)
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
