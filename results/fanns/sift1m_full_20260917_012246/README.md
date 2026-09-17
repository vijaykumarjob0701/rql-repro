# sift1m_full_20260917_012246

**Scope: FULL.** Label: `full SIFT1M (n=1000000, nq=100) — microbench`.

PRE/POST filtered microbench on SIFT1M (TexMex via HF `qbo-odp/sift1m`).
Synthetic Bernoulli predicates at selectivities {0.01, 0.05, 0.1, 0.5}.
Official `sift_groundtruth.ivecs` is unfiltered 100-NN; this run recomputes **filtered** GT on the loaded base subset/full set.

- Dataset: `SIFT1M full base N=1000000 + first 100 queries; d=128; mirror=HF qbo-odp/sift1m`
- Artifacts: `metrics.json`, `ENV.txt`, `plans/`
- NumPy brute PRE/POST plumbing — **not** FAISS/HNSW venue-grade P0 alone.
