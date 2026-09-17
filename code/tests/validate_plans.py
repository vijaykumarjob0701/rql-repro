#!/usr/bin/env python3
"""Validate schemas/examples/*.json against LogicalPlan / PhysicalPlan JSON Schemas.

Draft Hypothesis IR only — not a standard. Requires the ``jsonschema`` package.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]  # code/
REPO_ROOT = CODE.parent
SCHEMAS = CODE / "schemas"
EXAMPLES = SCHEMAS / "examples"
RESULTS = REPO_ROOT / "results" / "scratch" / "plan_schema"


def main() -> int:
    lines: list[str] = []
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:
        msg = "FAIL: jsonschema not installable/importable in this environment"
        print(msg)
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "validate.txt").write_text(msg + "\n", encoding="utf-8")
        return 1

    logical_schema = json.loads((SCHEMAS / "logical-plan.schema.json").read_text(encoding="utf-8"))
    physical_schema = json.loads((SCHEMAS / "physical-plan.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(logical_schema)
    Draft202012Validator.check_schema(physical_schema)
    lines.append("OK: both schemas are valid JSON Schema draft 2020-12")
    try:
        from importlib.metadata import version as _pkg_version
        ver = _pkg_version("jsonschema")
    except Exception:
        ver = "unknown"
    lines.append(f"jsonschema package available (version {ver})")

    logical_v = Draft202012Validator(logical_schema)
    physical_v = Draft202012Validator(physical_schema)

    files = sorted(EXAMPLES.glob("*.json"))
    if not files:
        lines.append("FAIL: no example JSON files under schemas/examples/")
        text = "\n".join(lines) + "\n"
        print(text, end="")
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "validate.txt").write_text(text, encoding="utf-8")
        return 1

    errors = 0
    for path in files:
        instance = json.loads(path.read_text(encoding="utf-8"))
        kind = instance.get("kind")
        if kind == "LogicalPlan":
            errs = sorted(logical_v.iter_errors(instance), key=lambda e: list(e.path))
        elif kind == "PhysicalPlan":
            errs = sorted(physical_v.iter_errors(instance), key=lambda e: list(e.path))
        else:
            lines.append(f"FAIL: {path.name}: unknown or missing kind={kind!r}")
            errors += 1
            continue
        if errs:
            errors += 1
            lines.append(f"FAIL: {path.name} ({kind})")
            for e in errs[:5]:
                loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
                lines.append(f"  - {loc}: {e.message}")
        else:
            lines.append(f"OK: {path.name} validates as {kind}")

    lines.append("")
    if errors:
        lines.append(f"RESULT: {errors} file(s) failed; {len(files) - errors} passed")
        rc = 1
    else:
        lines.append(f"RESULT: all {len(files)} example plan(s) passed")
        rc = 0

    text = "\n".join(lines) + "\n"
    print(text, end="")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "validate.txt").write_text(text, encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
