# sift1m_faiss_HNSW32_20260917_022017

**FAISS-index ANN microbench on SIFT1M** (stronger than brute NumPy).

- Index: **HNSW32** (`IndexHNSWFlat`, M=32, efConstruction=200, efSearch=64)
- Why HNSW32 (not IVF4096,Flat): no train/nprobe tuning; graph family; IDSelector PRE; efSearch depth knob.
- Base: N=1000000, d=128; queries: nq=1000; k=10; seed=42
- Selectivities: [0.01, 0.05, 0.1, 0.5]; modes PRE / POST
- Predicates: synthetic Bernoulli on ids (seed=42) — **not** real metadata attributes
- Filtered GT: exact `IndexFlatL2` + `IDSelectorBitmap` (not official unfiltered `sift_groundtruth.ivecs`)
- PRE: `SearchParametersHNSW` + `IDSelectorBitmap` on the full HNSW index
- POST: HNSW search top-(k×50) then predicate filter (no exact pad; <k survivors → shortfall)

## Caveats

- **Not** ACORN (or any paper) numbers — do not compare tables as reproduction.
- Synthetic predicates; single efSearch / candidate-mult setting (not a full depth sweep).
- Vanilla HNSW+filter recall drops at low selectivity (expected; motivates predicate-aware graph methods).
- Still missing live adapters / RAG judgments for venue-complete story.
- L2 on raw SIFT floats (TexMex convention); no L2-normalize.

Artifacts: `ENV.txt`, `README.md`, `WALL_TIME.txt`, `metrics.json`, `metrics.jsonl`, plus `plans/run.json`.
