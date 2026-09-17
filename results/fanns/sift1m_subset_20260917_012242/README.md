# sift1m_subset_20260917_012242

**Scope: SUBSET.** Label: `subset smoke (n=100000, nq=100) — not full P0`.

PRE/POST filtered microbench on SIFT1M (TexMex via HF `qbo-odp/sift1m`).
Synthetic Bernoulli predicates at selectivities {0.01, 0.05, 0.1, 0.5}.
Official `sift_groundtruth.ivecs` is unfiltered 100-NN; this run recomputes **filtered** GT on the loaded base subset/full set.

- Dataset: `SIFT1M subset first 100000 of base + first 100 queries; d=128; mirror=HF qbo-odp/sift1m`
- Artifacts: `metrics.json`, `ENV.txt`, `plans/`
- Do **not** treat subset smoke as venue-grade P0 alone.
