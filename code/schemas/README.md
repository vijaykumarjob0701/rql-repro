# RQL plan schemas — `0.1.0-draft`

**Date:** 2026-09-16 (Europe/Dublin)  
**Status:** **Hypothesis IR** freeze (draft). **Not** a published standard. Do not claim ANSI/Substrait-level stability.

Companion journal: [`../journal/0021-logical-physical-plan-schema-v0.1.md`](../journal/0021-logical-physical-plan-schema-v0.1.md).  
Grounding: [`../docs/08-algebra-sketch.md`](../docs/08-algebra-sketch.md), thesis §05 / §06 / §07, vendor matrix [`../docs/09-vendor-api-matrix.md`](../docs/09-vendor-api-matrix.md).

---

## Files

| Path | Role |
|------|------|
| [`logical-plan.schema.json`](logical-plan.schema.json) | JSON Schema draft **2020-12** for `LogicalPlan` |
| [`physical-plan.schema.json`](physical-plan.schema.json) | JSON Schema draft **2020-12** for `PhysicalPlan` |
| [`examples/`](examples/) | Valid example plan JSON (logical + physical) |
| Validator | [`../experiments/harness/validate_plans.py`](../experiments/harness/validate_plans.py) |
| Pass output | [`../experiments/results/plan_schema/validate.txt`](../experiments/results/plan_schema/validate.txt) |
| Planner stub | [`../experiments/harness/rql_planner/`](../experiments/harness/rql_planner/) (journal 0023; Logical→Physical) |

---

## Honesty labels

| Label | Meaning here |
|-------|----------------|
| **Established** | Literature/docs facts *cited by* operators (e.g. RRF formula, MaxSim, FANNS taxonomy, vendor API surfaces). |
| **Hypothesis** | RQL **naming, JSON encoding, compile packaging**, and capability-flag wiring in these schemas. |
| **Provisional** | Unreproduced AUTHOR metrics — **not** encoded as schema claims. |

These schemas freeze a **Hypothesis IR** so adapters and EXPLAIN can talk about the same trees. They do **not** make RQL a standard.

---

## LogicalPlan operators

Evidence ops (docs/08 + thesis §05):

`Search_dense` · `Search_bm25` · `Search_late` · `Filter` · `Union` · `Fuse_rrf` · `Fuse_linear` · `Fuse_ltr` · `Fuse_condorcet` · `Diversify` · `Rerank` · `Expand` · `Rewrite` · `Traverse` · `VSimJoin` · `Ext`

Optional top-level `capabilities` annotations mirror vendor-matrix flags (see below).

---

## PhysicalPlan nodes

| Node | Notes |
|------|-------|
| `FilterExec` | Modes: `PRE` / `POST` / `ITERATIVE` / `SUBGRAPH` / `SPECIALIZED` / `PARTITION` / `ROUTER` / `AUTO` |
| `AnnExec` | Index + search params (hnsw/ivf/diskann/…) |
| `Bm25Exec` | Lexical leaf |
| `FusionExec` | Families: `rrf` / `linear` / `ltr` / `condorcet`; `native` flag |
| `LateInteractExec` | Variants: `colbert` / `plaid` / `muvera` |
| `ShimCast` | Explicit client shim when native capability missing |
| `RerankExec` / `PassThrough` | Rerank + EXPLAIN bookkeeping |

Optional `budgets.recallTarget` / `budgets.latencyMs` / `budgets.aclSafe` (Hypothesis surface; BlinkDB dual-contract + ELP **Established** as AQP prior — journal **0031**; packaging Hypothesis; do not equate ε with recall@k).

---

## Map to vendor matrix capability flags

From [`docs/09-vendor-api-matrix.md`](../docs/09-vendor-api-matrix.md) (Established **docs-only** survey, journal 0020):

| Schema `capabilities.*` / physical field | Matrix column / implication |
|------------------------------------------|-----------------------------|
| `filterAnnComposition` | Filter+ANN composition (PRE / POST+iterative / leaf-propagated / hybrid-batches / UNKNOWN) |
| `hybridBm25Dense` | Hybrid / BM25+dense native path |
| `rrfNative` | First-class RRF (Qdrant/ES/OS/Milvus vs client shim) |
| `weightedFusionNative` | Weighted/score fusion (not interchangeable across vendors) |
| `multiVectorLate` | Multi-vector / late interaction native |
| `latePlaid` / `fdeMips` | PLAID / MUVERA rewrite ladder ads (Hypothesis compile) |
| `explainNative` | EXPLAIN / Profile visibility |
| `FusionExec.native` / `ShimCast` | Compile choice: native fuse vs explicit client CAST |
| `FilterExec.mode` | Negotiated physical filter strategy from advertised modes |

**Rule:** missing capability → rewrite, `ShimCast`, or hard error — never silent dense cosine for `Search_late`.

---

## Validate examples

```bash
# from repo root
tooling/.venv/bin/python experiments/harness/validate_plans.py
# or: python3 experiments/harness/validate_plans.py   # if jsonschema installed
```

Expect `OK` lines and exit code 0; captured under `experiments/results/plan_schema/validate.txt`.

### Toy textual frontend (journal 0022)

Schema-aligned `.rql` files in `examples/` parse via:

```bash
tooling/.venv/bin/python experiments/harness/test_rql_parser.py
tooling/.venv/bin/python experiments/harness/parse_rql.py parse schemas/examples/01-hybrid-rrf.rql --validate
```

Outputs land in `experiments/results/rql_parser/`. Tiny grammar: `experiments/harness/rql_parser/grammar.md` (Hypothesis; not a full SQL engine).

---



---

## Substrait / Calcite extension points (adjacency note)

**Date:** 2026-09-17 (Europe/Dublin) · journal [`0025`](../journal/0025-substrait-calcite-ir-adjacency.md)

These schemas are **Hypothesis IR**, Substrait-*inspired* and Calcite-*inspired* — **not** Substrait protobuf and **not** a Calcite `RelNode` binding.

| If we ever chase interchange… | Possible hook (still Hypothesis) |
|-------------------------------|----------------------------------|
| Substrait custom relations | Map `Search_*` / `Fuse_*` / `LateInteractExec` → `ExtensionLeafRel` / `ExtensionSingleRel` / `ExtensionMultiRel` with a documented `detail` schema |
| Substrait simple extensions | Encode similarity / fusion helpers as YAML function extensions (URN-scoped) — only if a consumer exists |
| Substrait `AdvancedExtension` | Budgets / EXPLAIN hints as *optimization*; semantic `ShimCast` as *enhancement* (must not be silently dropped) |
| Calcite-style traits | Today's `capabilities.*` + `FilterExec.mode` play an analogous role to calling-convention / physical traits |
| Calcite enumerable fallback | Explicit `ShimCast` when native RRF / late / iterative ads missing |

**Do not** bump `schemaVersion` solely for this note; no wire format claimed.

## Version

`schemaVersion` **const** `0.1.0-draft` on every document. Breaking changes bump the draft tag and journal a follow-up entry.
