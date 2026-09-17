#!/usr/bin/env python3
"""E2E CLI glue: toy .rql → parse → plan(profile) → emit(adapter) → run folder.

Offline / deterministic only. Never opens sockets or hits live vector DBs.
Hypothesis compile stack (journals 0022–0024 + 0026).

Usage (from companion repo root):
  python code/rql_pipeline.py \
      --inputs code/examples/toy --profiles qdrant,elasticsearch,pgvector \
      --out-dir results/e2e --validate --run-id smoke

  python code/rql_pipeline.py run-batch --inputs code/examples/toy --validate
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")

HERE = Path(__file__).resolve().parent  # code/
REPO = HERE  # schemas/ and examples/ live under code/
REPO_ROOT = HERE.parent  # companion repo root (rql-repro/)
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from rql_parser.parser import ParseError, parse_rql_file  # noqa: E402
from rql_planner.planner import PlanError, list_profiles, load_profile, plan_logical  # noqa: E402
from rql_adapters.emit import AdapterError, emit_plan, emit_to_files  # noqa: E402

DEFAULT_PROFILES = ("qdrant", "elasticsearch", "pgvector")
SCHEMA_VERSION = "0.1.0-draft"


def _repo_root() -> Path:
    return REPO


def _validate(instance: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errs = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda e: list(e.path),
    )
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in errs
    ]


def _stem_of(path: Path) -> str:
    name = path.name
    if name.endswith(".rql"):
        return name[: -len(".rql")]
    return path.stem


def _discover_rql(inputs: Path) -> list[Path]:
    if inputs.is_file():
        if inputs.suffix != ".rql":
            raise SystemExit(f"E2E_FAIL: expected .rql file, got {inputs}")
        return [inputs]
    if not inputs.is_dir():
        raise SystemExit(f"E2E_FAIL: inputs not found: {inputs}")
    files = sorted(inputs.glob("*.rql"))
    if not files:
        raise SystemExit(f"E2E_FAIL: no *.rql under {inputs}")
    return files


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")



def run_one(
    rql_path: Path,
    profile_name: str,
    run_dir: Path,
    *,
    validate: bool,
    late_rewrite: str | None,
) -> dict[str, Any]:
    """Run parse→plan→emit for one (file, profile). Returns a result record."""
    stem = _stem_of(rql_path)
    out = run_dir / stem / profile_name
    out.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "stem": stem,
        "profile": profile_name,
        "rql": str(rql_path.relative_to(REPO)) if rql_path.is_relative_to(REPO) else str(rql_path),
        "ok": False,
        "stages": {},
        "artifacts": [],
    }

    # --- parse ---
    try:
        logical = parse_rql_file(rql_path)
    except (ParseError, OSError) as e:
        record["error"] = f"PARSE_FAIL: {e}"
        _write_json(out / "result.json", record)
        return record

    logical_path = out / f"{stem}.logical.json"
    _write_json(logical_path, logical)
    record["artifacts"].append(str(logical_path.relative_to(run_dir)))
    record["stages"]["parse"] = "OK"

    if validate:
        schema = REPO / "schemas" / "logical-plan.schema.json"
        verrs = _validate(logical, schema)
        if verrs:
            record["error"] = "VALIDATE_FAIL: LogicalPlan"
            record["validate_errors"] = verrs[:10]
            _write_json(out / "result.json", record)
            return record
        record["stages"]["validate_logical"] = "OK"

    # --- plan ---
    try:
        profile = load_profile(profile_name)
        physical = plan_logical(
            logical,
            profile,
            logical_ref=str(logical_path.relative_to(REPO))
            if logical_path.is_relative_to(REPO)
            else str(logical_path),
            late_rewrite=late_rewrite,
        )
    except PlanError as e:
        record["error"] = f"PLAN_FAIL: {e}"
        _write_json(out / "result.json", record)
        return record

    physical_path = out / f"{stem}.{profile_name}.physical.json"
    _write_json(physical_path, physical)
    record["artifacts"].append(str(physical_path.relative_to(run_dir)))
    record["stages"]["plan"] = "OK"
    record["root_op"] = (physical.get("root") or {}).get("op")

    if validate:
        schema = REPO / "schemas" / "physical-plan.schema.json"
        verrs = _validate(physical, schema)
        if verrs:
            record["error"] = "VALIDATE_FAIL: PhysicalPlan"
            record["validate_errors"] = verrs[:10]
            _write_json(out / "result.json", record)
            return record
        record["stages"]["validate_physical"] = "OK"

    # --- emit (never network) ---
    try:
        art = emit_plan(physical, profile=profile_name)
        written = emit_to_files(physical, out, stem, profile=profile_name)
    except AdapterError as e:
        record["error"] = f"EMIT_FAIL: {e}"
        _write_json(out / "result.json", record)
        return record

    if not art.get("notExecuted") or not art.get("approximate"):
        record["error"] = "EMIT_FAIL: sketch missing notExecuted/approximate flags"
        _write_json(out / "result.json", record)
        return record

    for p in written:
        record["artifacts"].append(str(p.relative_to(run_dir)))
    record["stages"]["emit"] = "OK"
    record["vendor"] = art.get("vendor")
    record["emit_format"] = art.get("format")
    record["notExecuted"] = True
    record["ok"] = True
    _write_json(out / "result.json", record)
    return record


def run_batch(args: argparse.Namespace) -> int:
    inputs = Path(args.inputs)
    if not inputs.is_absolute():
        cwd_cand = (Path.cwd() / inputs).resolve()
        repo_cand = (REPO / inputs).resolve()
        inputs = cwd_cand if cwd_cand.exists() else repo_cand
    else:
        inputs = inputs.resolve()

    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    if not profiles:
        print("E2E_FAIL: empty --profiles", file=sys.stderr)
        return 1
    for p in profiles:
        try:
            load_profile(p)
        except PlanError as e:
            print(f"E2E_FAIL: {e}", file=sys.stderr)
            return 1

    rql_files = _discover_rql(inputs)

    out_base = Path(args.out_dir)
    if not out_base.is_absolute():
        out_base = (REPO_ROOT / out_base).resolve()
    run_id = args.run_id or "smoke"
    run_dir = out_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Manifest
    now = datetime.now(tz=DUBLIN)
    manifest = {
        "kind": "RqlE2ERun",
        "schemaVersion": "0.1.0-draft-e2e",
        "label": "Hypothesis",
        "notExecuted": True,
        "liveDb": False,
        "runId": run_id,
        "timestamp": now.isoformat(timespec="seconds"),
        "timezone": str(now.tzinfo),
        "inputs": str(inputs.relative_to(REPO)) if inputs.is_relative_to(REPO) else str(inputs),
        "profiles": profiles,
        "bundled_profiles": list_profiles(),
        "rql_files": [
            str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p) for p in rql_files
        ],
        "validate": bool(args.validate),
        "late_rewrite": args.late_rewrite,
        "honesty": (
            "Offline E2E glue only: parse → LogicalPlan → plan(profile) → "
            "PhysicalPlan → emit(adapter sketches). No live vector-DB calls."
        ),
    }
    _write_json(run_dir / "manifest.json", manifest)

    lines: list[str] = []
    lines.append("RQL E2E pipeline (Hypothesis; offline; notExecuted)")
    lines.append(f"run_id: {run_id}")
    lines.append(f"run_dir: {run_dir.relative_to(REPO) if run_dir.is_relative_to(REPO) else run_dir}")
    lines.append(f"inputs: {manifest['inputs']}")
    lines.append(f"profiles: {profiles}")
    lines.append(f"rql_files: {[Path(p).name for p in manifest['rql_files']]}")
    lines.append(f"validate: {args.validate}")
    lines.append(f"timestamp: {manifest['timestamp']}")
    lines.append("")

    ok = 0
    total = 0
    records: list[dict[str, Any]] = []
    for rql_path in rql_files:
        for pname in profiles:
            total += 1
            rec = run_one(
                rql_path,
                pname,
                run_dir,
                validate=bool(args.validate),
                late_rewrite=args.late_rewrite,
            )
            records.append(rec)
            tag = f"{rec['stem']}@{pname}"
            if rec.get("ok"):
                ok += 1
                lines.append(
                    f"OK: {tag} → root.op={rec.get('root_op')} "
                    f"vendor={rec.get('vendor')} emit={rec.get('emit_format')}"
                )
            else:
                err = rec.get("error", "unknown")
                lines.append(f"FAIL: {tag}: {err}")
                for v in (rec.get("validate_errors") or [])[:3]:
                    lines.append(f"  - {v}")

    lines.append("")
    lines.append(f"RESULT: ok={ok}/{total}")
    if args.validate:
        lines.append(f"schema_validate: enabled (LogicalPlan + PhysicalPlan {SCHEMA_VERSION})")
    lines.append("live_db: false")
    lines.append("notExecuted: true")

    summary = "\n".join(lines) + "\n"
    summary_path = run_dir / "summary.txt"
    summary_path.write_text(summary, encoding="utf-8")

    # Top-level validate log (requested path)
    validate_path = out_base / "run_validate.txt"
    validate_path.write_text(summary, encoding="utf-8")

    # Compact results index
    index = {
        "runId": run_id,
        "ok": ok,
        "total": total,
        "records": [
            {
                "stem": r["stem"],
                "profile": r["profile"],
                "ok": r["ok"],
                "root_op": r.get("root_op"),
                "error": r.get("error"),
            }
            for r in records
        ],
    }
    _write_json(run_dir / "index.json", index)

    print(summary, end="")
    print(f"wrote {summary_path.relative_to(REPO) if summary_path.is_relative_to(REPO) else summary_path}")
    print(f"wrote {validate_path.relative_to(REPO) if validate_path.is_relative_to(REPO) else validate_path}")
    return 0 if ok == total and total > 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rql_pipeline",
        description=(
            "E2E: .rql → LogicalPlan → PhysicalPlan(profile) → vendor emit sketches "
            "(offline; never hits live DBs)."
        ),
    )
    ap.add_argument(
        "command",
        nargs="?",
        default="run-batch",
        choices=["run-batch", "list-profiles"],
        help="Subcommand (default: run-batch)",
    )
    ap.add_argument(
        "--inputs",
        type=Path,
        default=REPO / "examples" / "toy",
        help="Directory of *.rql or a single .rql file",
    )
    ap.add_argument(
        "--profiles",
        default=",".join(DEFAULT_PROFILES),
        help="Comma-separated profile ids (default: qdrant,elasticsearch,pgvector)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "results" / "e2e",
        help="Base results directory (run folder created under it)",
    )
    ap.add_argument(
        "--run-id",
        default="smoke",
        help="Run folder name under out-dir (default: smoke)",
    )
    ap.add_argument(
        "--validate",
        action="store_true",
        help="Validate LogicalPlan and PhysicalPlan against JSON Schemas",
    )
    ap.add_argument(
        "--late-rewrite",
        choices=["colbert", "plaid", "muvera"],
        default=None,
        help="Optional Search_late rewrite preference passed to planner",
    )
    args = ap.parse_args(argv)

    if args.command == "list-profiles":
        for p in list_profiles():
            print(p)
        return 0
    return run_batch(args)


if __name__ == "__main__":
    raise SystemExit(main())
