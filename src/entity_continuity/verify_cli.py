"""Offline receipt verification command."""

import argparse
import json

from .engine import InvalidCase, load_json
from .verify import verify


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute an Entity Continuity synthetic receipt")
    parser.add_argument("case")
    parser.add_argument("pack")
    parser.add_argument("receipt")
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        result = verify(load_json(args.case), load_json(args.pack), args.as_of, load_json(args.receipt))
    except (InvalidCase, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
