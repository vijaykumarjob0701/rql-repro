# rql_planner — LogicalPlan → PhysicalPlan stub

**Status:** Hypothesis deterministic rules only. **Not** a cost-based optimizer.  
**Date:** 2026-09-16 (Europe/Dublin)  
**Journal:** [`../../../journal/0023-physical-planner-stub.md`](../../../journal/0023-physical-planner-stub.md)

## Rules

| Logical op | Physical mapping |
|------------|------------------|
| `Filter` | `FilterExec` mode via toy selectivity/ACL heuristics (`filter_mode.py`; aligned with `test_filter_strategy_chooser.py`) + FANNS pruningStrategy labels |
| `Fuse_rrf` | `FusionExec` `native=true` if profile `rrfNative`; else `ShimCast client_rrf` wrapping `native=false` |
| `Fuse_linear` | `FusionExec` native if `weightedFusionNative`; else `ShimCast client_linear` |
| `Search_late` | `LateInteractExec` (`colbert` default; optional `--late-rewrite plaid\|muvera` when advertised) |
| `Search_dense` / `Search_bm25` | `AnnExec` / `Bm25Exec` |

Profiles under `profiles/` are **docs-derived** flags from `docs/09-vendor-api-matrix.md` (journal 0020) — **not** live probes. No fabricated latency/recall.

## CLI

```bash
# from repo root
tooling/.venv/bin/python experiments/harness/plan_rql.py list-profiles
tooling/.venv/bin/python experiments/harness/plan_rql.py plan \\
  experiments/results/rql_parser/01-hybrid-rrf.logical.json \\
  --profile qdrant --validate
tooling/.venv/bin/python experiments/harness/test_rql_planner.py
```
