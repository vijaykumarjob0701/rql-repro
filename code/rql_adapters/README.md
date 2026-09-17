# rql_adapters — PhysicalPlan → vendor request emit stub

**Status:** Hypothesis / approximate sketches only. **Never** executed against live DBs.  
**Date:** 2026-09-17 ~00:00 IST (Europe/Dublin)  
**Journal:** [`../../../journal/0024-adapter-emit-stub.md`](../../../journal/0024-adapter-emit-stub.md)

## What this does

Takes schema-valid **PhysicalPlan** JSON (+ profile/vendor) and **emits** docs-shaped request artifacts as strings/JSON files:

| Vendor | Artifact |
|--------|----------|
| **qdrant** | Query API-shaped JSON (`filter` + `prefetch`/`fusion=rrf` or `nearest`) |
| **elasticsearch** | `retriever.rrf` / `knn` (+ `filter`) request JSON sketch |
| **pgvector** | SQL sketch (`ORDER BY embedding <=> … LIMIT`; iterative-scan comment if `ITERATIVE`) |

Every artifact is labeled `Hypothesis`, `approximate=true`, `notExecuted=true`.

## What this does **not** do

- No HTTP/gRPC/SQL connections
- No docker compose up
- No fabricated latency/recall
- Live smoke remains **HUMAN_TODO** (`experiments/protocols/03-adapter-smoke.md`)

## CLI

```bash
# from repo root
tooling/.venv/bin/python experiments/harness/emit_rql.py list-vendors
tooling/.venv/bin/python experiments/harness/emit_rql.py emit-batch \
  experiments/results/rql_planner/ \
  --stems 01-hybrid-rrf,02-filtered-dense \
  --profiles qdrant,elasticsearch,pgvector \
  --out-dir experiments/results/rql_adapters/
tooling/.venv/bin/python experiments/harness/test_rql_adapters.py
```
