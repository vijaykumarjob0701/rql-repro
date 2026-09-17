#!/usr/bin/env python3
"""Parse schemas/examples/*.rql (toy subset) → LogicalPlan; validate with jsonschema.

Writes real outputs under experiments/results/rql_parser/.
No fabricated retrieval metrics.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]  # code/
REPO_ROOT = CODE.parent
sys.path.insert(0, str(CODE))

from rql_parser import ParseError, parse_rql_file  # noqa: E402

EXAMPLES = CODE / "schemas" / "examples"
RESULTS = REPO_ROOT / "results" / "scratch" / "rql_parser"
SCHEMA = CODE / "schemas" / "logical-plan.schema.json"


def validate(plan: dict) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed"]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errs = sorted(
        Draft202012Validator(schema).iter_errors(plan),
        key=lambda e: list(e.path),
    )
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in errs
    ]


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    files = sorted(EXAMPLES.glob("*.rql"))
    lines: list[str] = []
    lines.append("Toy RQL parser → LogicalPlan (Hypothesis subset)")
    lines.append(f"examples_dir: {EXAMPLES}")
    lines.append(f"n_rql_files: {len(files)}")
    lines.append("")

    if not files:
        lines.append("FAIL: no *.rql under schemas/examples/")
        text = "\n".join(lines) + "\n"
        (RESULTS / "parse_validate.txt").write_text(text, encoding="utf-8")
        print(text, end="")
        return 1

    ok_parse = 0
    ok_valid = 0
    for path in files:
        out_json = RESULTS / f"{path.stem}.logical.json"
        try:
            plan = parse_rql_file(path)
        except ParseError as e:
            lines.append(f"PARSE_FAIL: {path.name}: {e}")
            continue
        out_json.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        ok_parse += 1
        verrs = validate(plan)
        if verrs:
            lines.append(f"VALIDATE_FAIL: {path.name} (wrote {out_json.name})")
            for v in verrs[:5]:
                lines.append(f"  - {v}")
        else:
            ok_valid += 1
            lines.append(
                f"OK: {path.name} → {out_json.name} "
                f"(root.op={plan['root'].get('op')})"
            )

    lines.append("")
    lines.append(
        f"RESULT: parse_ok={ok_parse}/{len(files)} validate_ok={ok_valid}/{len(files)}"
    )
    try:
        from rql_parser import parse_rql

        parse_rql("RETRIEVE c EMBED TEXT $q SEARCH DENSE CANDIDATES 5 QUERY 'x';")
        lines.append("NEG_FAIL: EMBED should have been rejected")
        neg_ok = False
    except ParseError:
        lines.append("OK: unsupported EMBED rejected (ParseError)")
        neg_ok = True

    rc = 0 if ok_parse == len(files) and ok_valid == len(files) and neg_ok else 1
    text = "\n".join(lines) + "\n"
    (RESULTS / "parse_validate.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
