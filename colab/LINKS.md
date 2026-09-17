# Google Colab notebook links

Stable Drive/Colab URLs for notebooks used in this research. Keep this file updated whenever a new Colab notebook is created or re-uploaded.

| Notebook (repo path) | Colab URL | Runtime used | Results path | Notes |
|----------------------|-----------|--------------|--------------|-------|
| [`fanns_microbench_colab.ipynb`](fanns_microbench_colab.ipynb) | https://colab.research.google.com/drive/1FH33zBXZezHLS3cSAR5nJQdELxX29s_A | T4 GPU (`faiss-gpu` 1.15.1) | [`../results/fanns/colab_synth_20260916_233628/`](../results/fanns/colab_synth_20260916_233628/) | Synthetic N=50k d=128 PRE/POST — **not P0** (SIFT1M skipped) |
| [`fanns_microbench_colab.ipynb`](fanns_microbench_colab.ipynb) | https://colab.research.google.com/drive/1FH33zBXZezHLS3cSAR5nJQdELxX29s_A | T4 runtime (FAISS **CPU** fallback) | [`../results/fanns/colab_synth_large_20260917_001447/`](../results/fanns/colab_synth_large_20260917_001447/) | N=200k synthetic PRE/POST; **SIFT1M download failed** (SSL hostname mismatch on corpus-texmex.irisa.fr) — not P0 |
| [`fanns_microbench_colab.ipynb`](fanns_microbench_colab.ipynb) | https://colab.research.google.com/drive/1FH33zBXZezHLS3cSAR5nJQdELxX29s_A | box CPU (NumPy brute) | [`../results/fanns/sift1m_subset_20260917_012242/`](../results/fanns/sift1m_subset_20260917_012242/) / [`sift1m_full_20260917_012246`](../results/fanns/sift1m_full_20260917_012246/) | **SIFT1M via HF mirror**; subset + full microbench (not FAISS P0) |

## How to open

Click the Colab URL while signed into the same Google account that owns the Drive file, or open from [Colab](https://colab.research.google.com/) → recent uploads.

## Policy

- Prefer committing the `.ipynb` in-repo **and** listing the live Colab URL here.
- Do not commit multi-GB datasets; only `metrics.json` / `ENV.txt` / `plans/`.

## SIFT1M for Colab (2026-09-17)

**Prefer Hugging Face** before TexMex HTTPS (TexMex HTTPS is dead: SSL/404):

```text
https://huggingface.co/datasets/qbo-odp/sift1m/resolve/main/sift_base.fvecs
https://huggingface.co/datasets/qbo-odp/sift1m/resolve/main/sift_query.fvecs
https://huggingface.co/datasets/qbo-odp/sift1m/resolve/main/sift_groundtruth.ivecs
# optional: sift_learn.fvecs
```

FTP fallback: `ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz`  
Digests + script: companion `rql-repro/datasets/REGISTRY.md` / `download_sift1m.sh`.  
Local microbench results: `sift1m_subset_20260917_012242`, `sift1m_full_20260917_012246`.

