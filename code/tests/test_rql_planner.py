#!/usr/bin/env python3
"""Plan 4 parsed LogicalPlans × 3 profiles → PhysicalPlan; validate with jsonschema.

Writes real outputs under experiments/results/rql_planner/.
No fabricated retrieval metrics. Hypothesis planner stub only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]  # code/
REPO_ROOT = CODE.parent
sys.path.insert(0, str(CODE))

from rql_planner import PlanError, list_profiles, load_profile, plan_logical  # noqa: E402
from rql_planner.filter_mode import choose_filter_mode  # noqa: E402

LOGICAL_DIR = REPO_ROOT / "results" / "scratch" / "rql_parser"
RESULTS = REPO_ROOT / "results" / "scratch" / "rql_planner"
SCHEMA = CODE / "schemas" / "physical-plan.schema.json"
PROFILES = ["qdrant", "elasticsearch", "pgvector"]


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


def _find_op(node: dict, op: str) -> dict | None:
    if node.get("op") == op:
        return node
    if "input" in node and isinstance(node["input"], dict):
        found = _find_op(node["input"], op)
        if found:
            return found
    for child in node.get("inputs") or []:
        if isinstance(child, dict):
            found = _find_op(child, op)
            if found:
                return found
    return None


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    files = sorted(LOGICAL_DIR.glob("*.logical.json"))
    lines: list[str] = []
    lines.append("LogicalPlan → PhysicalPlan planner stub (Hypothesis)")
    lines.append(f"logical_dir: {LOGICAL_DIR}")
    lines.append(f"profiles: {PROFILES}")
    lines.append(f"bundled_profiles: {list_profiles()}")
    lines.append(f"n_logical: {len(files)}")
    lines.append("")

    if len(files) < 4:
        lines.append(f"FAIL: expected ≥4 logical JSONs, found {len(files)}")
        text = "\n".join(lines) + "\n"
        (RESULTS / "plan_validate.txt").write_text(text, encoding="utf-8")
        print(text, end="")
        return 1

    ok_plan = 0
    ok_valid = 0
    total = 0
    assertions_ok = True

    for path in files:
        logical = json.loads(path.read_text(encoding="utf-8"))
        stem = path.name.replace(".logical.json", "")
        for pname in PROFILES:
            total += 1
            try:
                profile = load_profile(pname)
                physical = plan_logical(
                    logical, profile, logical_ref=str(path.relative_to(REPO_ROOT))
                )
            except PlanError as e:
                lines.append(f"PLAN_FAIL: {path.name}@{pname}: {e}")
                assertions_ok = False
                continue
            out_path = RESULTS / f"{stem}.{pname}.physical.json"
            out_path.write_text(
                json.dumps(physical, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            ok_plan += 1
            verrs = validate(physical)
            if verrs:
                lines.append(f"VALIDATE_FAIL: {out_path.name}")
                for v in verrs[:5]:
                    lines.append(f"  - {v}")
                assertions_ok = False
            else:
                ok_valid += 1
                root_op = physical["root"].get("op")
                lines.append(
                    f"OK: {path.name} + {pname} → {out_path.name} (root.op={root_op})"
                )

            # Deterministic rule assertions (integrity)
            try:
                if stem == "01-hybrid-rrf":
                    if pname in ("qdrant", "elasticsearch"):
                        assert physical["root"]["op"] == "FusionExec"
                        assert physical["root"]["native"] is True
                        assert physical["root"]["family"] == "rrf"
                    elif pname == "pgvector":
                        assert physical["root"]["op"] == "ShimCast"
                        assert physical["root"]["shim"] == "client_rrf"
                        fuse = physical["root"]["input"]
                        assert fuse["op"] == "FusionExec" and fuse["native"] is False
                if stem == "02-filtered-dense":
                    assert physical["root"]["op"] == "FilterExec"
                    mode = physical["root"]["mode"]
                    if pname == "pgvector":
                        # acl_hard + ann_iterator → ITERATIVE
                        assert mode == "ITERATIVE", mode
                    else:
                        # acl_hard without iterator → PRE
                        assert mode == "PRE", mode
                    assert physical["root"]["predicate"].get("aclHard") is True
                if stem == "03-late":
                    late = physical["root"]
                    assert late["op"] == "LateInteractExec"
                    if pname == "qdrant":
                        assert late["variant"] == "colbert"
                    else:
                        # no multiVectorLate → still colbert with honesty note
                        assert late["variant"] == "colbert"
                if stem == "04-hybrid-linear":
                    # Filter over Fuse_linear
                    assert physical["root"]["op"] == "FilterExec"
                    fuse = _find_op(physical["root"], "FusionExec")
                    assert fuse is not None and fuse["family"] == "linear"
                    if pname in ("qdrant", "elasticsearch"):
                        assert fuse["native"] is True
                        assert _find_op(physical["root"], "ShimCast") is None
                    else:
                        shim = _find_op(physical["root"], "ShimCast")
                        assert shim is not None and shim["shim"] == "client_linear"
                        assert fuse["native"] is False
            except AssertionError as e:
                lines.append(f"ASSERT_FAIL: {stem}@{pname}: {e}")
                assertions_ok = False

    # Filter-mode unit alignment with chooser ideas
    pg = load_profile("pgvector")
    qd = load_profile("qdrant")
    acl_pred = {"expr": "tenant_id = 'acme'", "aclHard": True}
    assert choose_filter_mode(acl_pred, pg) == "ITERATIVE"
    assert choose_filter_mode(acl_pred, qd) == "PRE"
    lines.append("OK: filter_mode acl heuristics (pgvector=ITERATIVE, qdrant=PRE)")

    lines.append("")
    lines.append(
        f"RESULT: plan_ok={ok_plan}/{total} validate_ok={ok_valid}/{total} "
        f"assertions={'OK' if assertions_ok else 'FAIL'}"
    )
    rc = 0 if ok_plan == total and ok_valid == total and assertions_ok else 1
    text = "\n".join(lines) + "\n"
    (RESULTS / "plan_validate.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
