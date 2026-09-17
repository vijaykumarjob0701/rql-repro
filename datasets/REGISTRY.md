# Dataset registry

**Date:** 2026-09-17 (Europe/Dublin)  
**Policy:** Do **not** commit multi-GB binaries. Record URL, license, how to obtain, and digests **after** you download. Digests below marked `TBD — fill after download` are intentional placeholders — **do not invent**.

Local raw files (gitignored): `datasets/data/`.

## Primary (P0 FANNS candidate)

| Dataset | URL | License / terms | How to obtain | Digest (sha256) | Ground truth | Local path |
|---------|-----|-----------------|---------------|-----------------|--------------|------------|
| **SIFT1M** (ANN_SIFT1B subset / TexMex) | http://corpus-texmex.irisa.fr/ (ANN_SIFT1M files) | Check TexMex / IRISA terms before download | See [`scripts/download_sift1m.md`](scripts/download_sift1m.md) | **TBD — fill after download** (base/learn/query/groundtruth `.fvecs`/`.ivecs`) | Included as `sift_groundtruth.ivecs` | `datasets/data/sift1m/` |

Expected files (names may vary by mirror): `sift_base.fvecs`, `sift_learn.fvecs`, `sift_query.fvecs`, `sift_groundtruth.ivecs`.

## Optional (RAG / retrieval judgments — not required for offline smoke)

| Dataset | URL | License | How to obtain | Digest (sha256) | Notes |
|---------|-----|---------|---------------|-----------------|-------|
| **MS MARCO** (passage) | https://microsoft.github.io/msmarco/ | Microsoft research license — accept terms | Official MS MARCO download page | **TBD — fill after download** | For future RAG judgment protocols |
| **BEIR** (subset as needed) | https://github.com/beir-cellar/beir | Per-dataset licenses inside BEIR | `pip`/BEIR loaders or official dumps | **TBD — fill after download** | Do not bulk-commit corpora |

## Synthetic (committed / regenerable)

| Fixture | Generator | Path | Notes |
|---------|-----------|------|-------|
| Tiny Gaussian | [`synthetic/generate_gaussian.py`](synthetic/generate_gaussian.py) | [`synthetic/fixtures/tiny/`](synthetic/fixtures/tiny/) | Small; for CI / offline smoke only — **not P0** |

## Filling digests

```bash
# Example after download (run locally; commit the hex digests into this table):
sha256sum datasets/data/sift1m/*
```

Never paste paper-table recall numbers into metrics files.
