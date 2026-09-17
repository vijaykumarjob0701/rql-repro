# Bench harnesses

- [`fanns_sift1m_microbench.py`](fanns_sift1m_microbench.py) — PRE/POST filtered microbench on SIFT1M (HF cache).
  - Default: **subset** first 100k base + 100 queries (smoke).
  - `--full`: attempt N=1M (memory permitting).
  - Writes `results/fanns/sift1m_<run_id>/` and copies to research `experiments/results/fanns/` when present.

Requires: `bash datasets/scripts/download_sift1m.sh` first.
