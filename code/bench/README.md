# Bench harnesses

- [`fanns_sift1m_microbench.py`](fanns_sift1m_microbench.py) — PRE/POST filtered microbench on SIFT1M (NumPy brute; plumbing).
  - Default: **subset** first 100k base + 100 queries (smoke).
  - `--full`: attempt N=1M (memory permitting).
- [`fanns_sift1m_faiss_microbench.py`](fanns_sift1m_faiss_microbench.py) — **FAISS-index** filtered-ANN microbench (protocol 01).
  - Primary index: **HNSW32** (`IndexHNSWFlat`); PRE via `IDSelectorBitmap`, POST via top-(k×mult) then filter.
  - Filtered GT: exact `IndexFlatL2` + selector (not official unfiltered GT).
  - Default: full base + 1000 queries; writes `results/fanns/sift1m_faiss_HNSW32_<run_id>/`.

Both copy into research `experiments/results/fanns/` when that tree exists.

Requires: `bash datasets/scripts/download_sift1m.sh` first; FAISS script needs `faiss-cpu` in `.venv`.
