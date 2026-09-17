"""CLI: python -m rql_planner plan LOGICAL.json --profile NAME [--out …] [--validate]
         python -m rql_planner plan-batch DIR --profiles a,b,c --out-dir DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .planner import PlanError, list_profiles, load_profile, plan_logical


def _validate(plan: dict, schema_path: Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errs = sorted(
        Draft202012Validator(schema).iter_errors(plan),
        key=lambda e: list(e.path),
    )
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in errs
    ]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def cmd_plan(args: argparse.Namespace) -> int:
    try:
        logical = json.loads(args.path.read_text(encoding="utf-8"))
        profile = load_profile(args.profile)
        physical = plan_logical(
            logical,
            profile,
            logical_ref=str(args.path),
            late_rewrite=args.late_rewrite,
        )
    except (OSError, json.JSONDecodeError, PlanError) as e:
        print(f"PLAN_FAIL: {args.path}: {e}", file=sys.stderr)
        return 1

    text = json.dumps(physical, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"OK: wrote {args.out}")
    else:
        sys.stdout.write(text)

    if args.validate:
        schema = args.schema or (_repo_root() / "schemas" / "physical-plan.schema.json")
        verrs = _validate(physical, schema)
        if verrs:
            print(f"VALIDATE_FAIL: {args.path}", file=sys.stderr)
            for v in verrs[:10]:
                print(f"  - {v}", file=sys.stderr)
            return 2
        print(f"OK: validates as PhysicalPlan against {schema.name}")
    return 0


def cmd_plan_batch(args: argparse.Namespace) -> int:
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    if not profiles:
        print("PLAN_FAIL: empty --profiles", file=sys.stderr)
        return 1
    src = args.dir
    files = sorted(src.glob("*.logical.json"))
    if not files:
        files = sorted(src.glob("*.json"))
        files = [f for f in files if "logical" in f.name or True]
        # Prefer *.logical.json; if none, take files whose kind is LogicalPlan
        filtered = []
        for f in sorted(src.glob("*.json")):
            try:
                inst = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if inst.get("kind") == "LogicalPlan":
                filtered.append(f)
        files = filtered

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = args.schema or (_repo_root() / "schemas" / "physical-plan.schema.json")
    lines: list[str] = []
    ok = 0
    total = 0
    for path in files:
        logical = json.loads(path.read_text(encoding="utf-8"))
        stem = path.name.replace(".logical.json", "").replace(".json", "")
        for pname in profiles:
            total += 1
            try:
                profile = load_profile(pname)
                physical = plan_logical(
                    logical,
                    profile,
                    logical_ref=str(path),
                    late_rewrite=args.late_rewrite,
                )
            except PlanError as e:
                lines.append(f"PLAN_FAIL: {path.name}@{pname}: {e}")
                continue
            out_name = f"{stem}.{pname}.physical.json"
            out_path = out_dir / out_name
            out_path.write_text(
                json.dumps(physical, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            if args.validate:
                verrs = _validate(physical, schema)
                if verrs:
                    lines.append(f"VALIDATE_FAIL: {out_name}")
                    for v in verrs[:3]:
                        lines.append(f"  - {v}")
                    continue
            ok += 1
            root_op = physical["root"].get("op")
            lines.append(f"OK: {path.name} + {pname} → {out_name} (root.op={root_op})")

    lines.append("")
    lines.append(f"RESULT: validate_ok={ok}/{total}" if args.validate else f"RESULT: planned={ok}/{total}")
    summary = "\n".join(lines) + "\n"
    summary_path = out_dir / "plan_validate.txt"
    summary_path.write_text(summary, encoding="utf-8")
    print(summary, end="")
    print(f"wrote {summary_path}")
    return 0 if ok == total and total > 0 else 1


def cmd_list_profiles(_args: argparse.Namespace) -> int:
    for p in list_profiles():
        print(p)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Hypothesis LogicalPlan → PhysicalPlan planner stub"
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Plan one LogicalPlan JSON")
    p_plan.add_argument("path", type=Path, help="LogicalPlan JSON path")
    p_plan.add_argument(
        "--profile",
        required=True,
        help="Profile id (qdrant|elasticsearch|pgvector) or path to JSON",
    )
    p_plan.add_argument("--out", type=Path, default=None)
    p_plan.add_argument("--validate", action="store_true")
    p_plan.add_argument("--schema", type=Path, default=None)
    p_plan.add_argument(
        "--late-rewrite",
        choices=["colbert", "plaid", "muvera"],
        default=None,
        help="Optional Search_late rewrite preference",
    )
    p_plan.set_defaults(func=cmd_plan)

    p_batch = sub.add_parser("plan-batch", help="Plan all LogicalPlans in a directory")
    p_batch.add_argument("dir", type=Path, help="Directory of LogicalPlan JSON")
    p_batch.add_argument(
        "--profiles",
        default="qdrant,elasticsearch,pgvector",
        help="Comma-separated profile ids",
    )
    p_batch.add_argument("--out-dir", type=Path, required=True)
    p_batch.add_argument("--validate", action="store_true")
    p_batch.add_argument("--schema", type=Path, default=None)
    p_batch.add_argument(
        "--late-rewrite",
        choices=["colbert", "plaid", "muvera"],
        default=None,
    )
    p_batch.set_defaults(func=cmd_plan_batch)

    p_list = sub.add_parser("list-profiles", help="List bundled profile ids")
    p_list.set_defaults(func=cmd_list_profiles)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
