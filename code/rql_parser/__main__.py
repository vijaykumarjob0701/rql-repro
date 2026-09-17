"""CLI: python -m rql_parser parse path.rql [--out out.json] [--validate]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python -m rql_parser` from harness/, or via parse_rql.py
from .parser import ParseError, parse_rql, parse_rql_file


def _validate(plan: dict, schema_path: Path) -> list[str]:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errs = sorted(
        Draft202012Validator(schema).iter_errors(plan),
        key=lambda e: list(e.path),
    )
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}" for e in errs]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Toy RQL → LogicalPlan JSON (Hypothesis)")
    ap.add_argument("command", choices=["parse"], help="Subcommand")
    ap.add_argument("path", type=Path, help="Path to .rql file")
    ap.add_argument("--out", type=Path, default=None, help="Write JSON here")
    ap.add_argument(
        "--validate",
        action="store_true",
        help="Validate against schemas/logical-plan.schema.json",
    )
    ap.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Override schema path",
    )
    args = ap.parse_args(argv)

    try:
        plan = parse_rql_file(args.path)
    except ParseError as e:
        print(f"PARSE_FAIL: {args.path}: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"IO_FAIL: {args.path}: {e}", file=sys.stderr)
        return 1

    text = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"OK: wrote {args.out}")
    else:
        sys.stdout.write(text)

    if args.validate:
        repo = Path(__file__).resolve().parents[3]
        schema = args.schema or (repo / "schemas" / "logical-plan.schema.json")
        verrs = _validate(plan, schema)
        if verrs:
            print(f"VALIDATE_FAIL: {args.path}", file=sys.stderr)
            for v in verrs[:10]:
                print(f"  - {v}", file=sys.stderr)
            return 2
        print(f"OK: validates as LogicalPlan against {schema.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
