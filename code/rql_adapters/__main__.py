"""CLI: emit vendor request sketches from PhysicalPlan JSON (never live DB).

Usage (from repo root):
  tooling/.venv/bin/python experiments/harness/emit_rql.py emit \\
      experiments/results/rql_planner/01-hybrid-rrf.qdrant.physical.json
  tooling/.venv/bin/python experiments/harness/emit_rql.py emit-batch \\
      experiments/results/rql_planner/ \\
      --stems 01-hybrid-rrf,02-filtered-dense \\
      --out-dir experiments/results/rql_adapters/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .emit import AdapterError, emit_plan, emit_to_files, list_vendors, resolve_vendor


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def cmd_list_vendors(_args: argparse.Namespace) -> int:
    for v in list_vendors():
        print(v)
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    try:
        physical = json.loads(args.path.read_text(encoding="utf-8"))
        art = emit_plan(physical, profile=args.profile)
    except (OSError, json.JSONDecodeError, AdapterError) as e:
        print(f"EMIT_FAIL: {args.path}: {e}", file=sys.stderr)
        return 1

    if args.out_dir:
        stem = args.stem or args.path.name.replace(".physical.json", "").rsplit(".", 1)[0]
        # Prefer stem from filename like 01-hybrid-rrf.qdrant.physical.json → 01-hybrid-rrf
        name = args.path.name
        if name.endswith(".physical.json"):
            base = name[: -len(".physical.json")]
            for v in list_vendors():
                suf = f".{v}"
                if base.endswith(suf):
                    stem = args.stem or base[: -len(suf)]
                    break
            else:
                stem = args.stem or base
        paths = emit_to_files(physical, args.out_dir, stem, profile=args.profile)
        for p in paths:
            print(f"OK: wrote {p}")
    else:
        # stdout: full artifact
        sys.stdout.write(json.dumps(art, indent=2, ensure_ascii=False) + "\n")
    print(
        f"OK: vendor={art['vendor']} format={art['format']} "
        f"label={art['label']} notExecuted={art['notExecuted']}"
    )
    return 0


def cmd_emit_batch(args: argparse.Namespace) -> int:
    stems = [s.strip() for s in args.stems.split(",") if s.strip()]
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    if not stems or not profiles:
        print("EMIT_FAIL: empty --stems or --profiles", file=sys.stderr)
        return 1
    src = args.dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    ok = 0
    total = 0
    for stem in stems:
        for pname in profiles:
            total += 1
            path = src / f"{stem}.{pname}.physical.json"
            if not path.is_file():
                lines.append(f"EMIT_FAIL: missing {path.name}")
                continue
            try:
                physical = json.loads(path.read_text(encoding="utf-8"))
                # sanity: resolved vendor matches filename profile when possible
                vendor = resolve_vendor(physical, profile=pname)
                paths = emit_to_files(physical, out_dir, stem, profile=pname)
            except (OSError, json.JSONDecodeError, AdapterError) as e:
                lines.append(f"EMIT_FAIL: {path.name}: {e}")
                continue
            ok += 1
            lines.append(f"OK: {stem}@{vendor} → {', '.join(p.name for p in paths)}")
    summary = out_dir / "emit_summary.txt"
    header = [
        "PhysicalPlan → vendor request emit stub (Hypothesis sketches; not executed)",
        f"src: {src}",
        f"out: {out_dir}",
        f"stems: {stems}",
        f"profiles: {profiles}",
        f"ok: {ok}/{total}",
        "",
    ]
    text = "\n".join(header + lines) + "\n"
    summary.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if ok == total else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="emit_rql",
        description="Emit Hypothesis vendor request sketches from PhysicalPlan JSON (no live DB).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list-vendors", help="List supported emit vendors")
    p_list.set_defaults(func=cmd_list_vendors)

    p_emit = sub.add_parser("emit", help="Emit one PhysicalPlan")
    p_emit.add_argument("path", type=Path)
    p_emit.add_argument("--profile", default=None, help="Override vendor/profile")
    p_emit.add_argument("--out-dir", type=Path, default=None)
    p_emit.add_argument("--stem", default=None)
    p_emit.set_defaults(func=cmd_emit)

    p_batch = sub.add_parser("emit-batch", help="Emit stem×profile matrix")
    p_batch.add_argument("dir", type=Path, help="Directory of *.physical.json")
    p_batch.add_argument(
        "--stems",
        default="01-hybrid-rrf,02-filtered-dense",
        help="Comma-separated plan stems",
    )
    p_batch.add_argument(
        "--profiles",
        default="qdrant,elasticsearch,pgvector",
        help="Comma-separated profiles/vendors",
    )
    p_batch.add_argument(
        "--out-dir",
        type=Path,
        default=_repo_root() / "experiments" / "results" / "rql_adapters",
    )
    p_batch.set_defaults(func=cmd_emit_batch)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
