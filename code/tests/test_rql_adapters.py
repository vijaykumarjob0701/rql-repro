#!/usr/bin/env python3
"""Emit vendor sketches for hybrid-rrf + filtered-dense × 3 profiles.

Writes under experiments/results/rql_adapters/.
No live DB calls. Hypothesis / approximate only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]  # code/
REPO_ROOT = CODE.parent
sys.path.insert(0, str(CODE))

from rql_adapters import AdapterError, emit_plan, emit_to_files, list_vendors  # noqa: E402

PHYSICAL_DIR = REPO_ROOT / "results" / "scratch" / "rql_planner"
RESULTS = REPO_ROOT / "results" / "scratch" / "rql_adapters"
STEMS = ["01-hybrid-rrf", "02-filtered-dense"]
PROFILES = ["qdrant", "elasticsearch", "pgvector"]


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("PhysicalPlan → vendor emit stub (Hypothesis sketches; notExecuted)")
    lines.append(f"physical_dir: {PHYSICAL_DIR}")
    lines.append(f"vendors: {list_vendors()}")
    lines.append(f"stems: {STEMS}")
    lines.append(f"profiles: {PROFILES}")
    lines.append("")

    ok = 0
    total = 0
    assertions_ok = True

    for stem in STEMS:
        for pname in PROFILES:
            total += 1
            path = PHYSICAL_DIR / f"{stem}.{pname}.physical.json"
            if not path.is_file():
                lines.append(f"EMIT_FAIL: missing {path.name}")
                assertions_ok = False
                continue
            physical = json.loads(path.read_text(encoding="utf-8"))
            try:
                art = emit_plan(physical, profile=pname)
                written = emit_to_files(physical, RESULTS, stem, profile=pname)
            except AdapterError as e:
                lines.append(f"EMIT_FAIL: {path.name}: {e}")
                assertions_ok = False
                continue

            # --- assertions ---
            if art.get("label") != "Hypothesis":
                lines.append(f"ASSERT_FAIL: {stem}@{pname}: label != Hypothesis")
                assertions_ok = False
            if not art.get("approximate") or not art.get("notExecuted"):
                lines.append(f"ASSERT_FAIL: {stem}@{pname}: must be approximate+notExecuted")
                assertions_ok = False
            if art.get("vendor") != pname:
                lines.append(
                    f"ASSERT_FAIL: {stem}@{pname}: vendor={art.get('vendor')} != profile"
                )
                assertions_ok = False

            body = art["body"]
            if pname == "qdrant":
                if stem == "01-hybrid-rrf":
                    if "prefetch" not in body and not body.get("_client_rrf_required"):
                        # native path needs prefetch
                        if "prefetch" not in body:
                            lines.append(f"ASSERT_FAIL: {stem}@qdrant: expected prefetch")
                            assertions_ok = False
                    if body.get("query", {}).get("fusion") != "rrf" and not body.get(
                        "_client_rrf_required"
                    ):
                        # native should have fusion=rrf
                        if physical["root"].get("op") == "FusionExec" or (
                            physical["root"].get("op") == "ShimCast"
                        ):
                            if body.get("query", {}).get("fusion") != "rrf":
                                # for native qdrant hybrid, fusion must be rrf
                                if physical["root"].get("native") or (
                                    physical["root"].get("op") == "FusionExec"
                                    and physical["root"].get("native")
                                ):
                                    pass
                    # Stronger check: qdrant hybrid native plan has FusionExec native
                    root = physical["root"]
                    if root.get("op") == "FusionExec" and root.get("native"):
                        if body.get("query", {}).get("fusion") != "rrf":
                            lines.append("ASSERT_FAIL: qdrant native RRF missing fusion=rrf")
                            assertions_ok = False
                        if not body.get("prefetch"):
                            lines.append("ASSERT_FAIL: qdrant native RRF missing prefetch")
                            assertions_ok = False
                if stem == "02-filtered-dense":
                    if "filter" not in body:
                        lines.append("ASSERT_FAIL: filtered-dense@qdrant missing filter")
                        assertions_ok = False
                    if "query" not in body:
                        lines.append("ASSERT_FAIL: filtered-dense@qdrant missing query")
                        assertions_ok = False

            elif pname == "elasticsearch":
                if stem == "01-hybrid-rrf":
                    rrf = (body.get("retriever") or {}).get("rrf")
                    if not rrf:
                        lines.append("ASSERT_FAIL: hybrid-rrf@es missing retriever.rrf")
                        assertions_ok = False
                    else:
                        if "retrievers" not in rrf:
                            lines.append("ASSERT_FAIL: es rrf missing retrievers")
                            assertions_ok = False
                if stem == "02-filtered-dense":
                    knn = body.get("knn") or {}
                    if "filter" not in knn:
                        lines.append("ASSERT_FAIL: filtered-dense@es knn missing filter")
                        assertions_ok = False

            elif pname == "pgvector":
                sql = body.get("sql") if isinstance(body, dict) else str(body)
                if "<=>" not in sql and "ts_rank" not in sql and "LateInteract" not in sql:
                    # hybrid has both branches
                    if "ORDER BY" not in sql and "ShimCast" not in sql and "--" not in sql:
                        lines.append(f"ASSERT_FAIL: {stem}@pgvector SQL sketch too empty")
                        assertions_ok = False
                if stem == "02-filtered-dense":
                    mode = physical["root"].get("mode")
                    if mode == "ITERATIVE" and "ITERATIVE" not in sql and "iterative" not in sql:
                        lines.append("ASSERT_FAIL: ITERATIVE plan missing iterative comment")
                        assertions_ok = False
                    if "<=>" not in sql:
                        lines.append("ASSERT_FAIL: filtered-dense@pgvector missing <=>")
                        assertions_ok = False
                # ensure .request.sql written
                sql_files = [p for p in written if p.suffix == ".sql"]
                if not sql_files:
                    lines.append(f"ASSERT_FAIL: {stem}@pgvector no .sql file written")
                    assertions_ok = False

            ok += 1
            lines.append(
                f"OK: {stem}@{pname} format={art['format']} files={[p.name for p in written]}"
            )

    lines.append("")
    lines.append(f"emit_ok: {ok}/{total}")
    lines.append(f"assertions_ok: {assertions_ok}")
    if ok == total and assertions_ok:
        lines.append("PASS")
        rc = 0
    else:
        lines.append("FAIL")
        rc = 1

    text = "\n".join(lines) + "\n"
    (RESULTS / "emit_validate.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
