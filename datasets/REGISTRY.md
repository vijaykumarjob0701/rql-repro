# Dataset registry

**Date:** 2026-09-17 (Europe/Dublin)  
**Policy:** Do **not** commit multi-GB binaries. Record URL, license, how to obtain, and digests **after** you download. Digests below are real SHA-256 from the Hugging Face mirror download on 2026-09-17.

Local raw files (gitignored): `datasets/cache/` (preferred) or `datasets/data/`.

## Primary (P0 FANNS candidate)

| Dataset | URL | License / terms | How to obtain | Digest (sha256) | Ground truth | Local path |
|---------|-----|-----------------|---------------|-----------------|--------------|------------|
| **SIFT1M** (ANN_SIFT1B subset / TexMex) | Preferred mirror: https://huggingface.co/datasets/qbo-odp/sift1m · FTP fallback: ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz · **TexMex HTTPS dead** (SSL/404 as of 2026-09-17) | INRIA TexMex / academic ANN evaluation; HF `qbo-odp/sift1m` is a **redistribution mirror** — review TexMex / IRISA terms | See [`scripts/download_sift1m.md`](scripts/download_sift1m.md) / [`scripts/download_sift1m.sh`](scripts/download_sift1m.sh) | see file digests below | Included as `sift_groundtruth.ivecs` (100-NN, unfiltered) | `datasets/cache/sift1m/` |

### SIFT1M file digests (Hugging Face `qbo-odp/sift1m`, 2026-09-17 Europe/Dublin)

| File | Bytes | sha256 |
|------|------:|--------|
| `sift_base.fvecs` | 516000000 | `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816` |
| `sift_query.fvecs` | 5160000 | `f7fc9be140accdfd64116c2fa2365ecdb69b8f084970c6b0532db5ff79ac8fdc` |
| `sift_groundtruth.ivecs` | 4040000 | `2b71de0a8d5a83e6a84eec3e23fb8b611d8801dd9b3a6cd62f070ab65ea65f4f` |
| `sift_learn.fvecs` (optional) | 51600000 | `331bc82b6a0e89465776a3ba0c2113e0bd0cceaa014ec3ed639bc8b981af72ea` |

Expected layout: `sift_base.fvecs` (N=1e6, d=128), `sift_query.fvecs` (nq=1e4, d=128), `sift_groundtruth.ivecs` (nq=1e4, 100-NN), optional `sift_learn.fvecs` (N=1e5).

### Alternate mirrors (documented)

| Mirror | Status (2026-09-17) | Notes |
|--------|---------------------|-------|
| Hugging Face `qbo-odp/sift1m` HTTPS | **Working** (preferred) | Same TexMex `.fvecs`/`.ivecs` layout |
| `ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz` | Working (~168MB tarball) | Official IRISA FTP |
| `http://ann-benchmarks.com/sift-128-euclidean.hdf5` | Working (~525MB) | **Different format** (HDF5); not drop-in for fvecs loaders |
| `https://corpus-texmex.irisa.fr/...` | **Dead** (SSL hostname mismatch / 404) | Do not rely on for Colab or CI |

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
# After download (local cache is gitignored; commit hex digests into this table):
sha256sum datasets/cache/sift1m/*
# or: cat datasets/cache/sift1m/SHA256SUMS
```

Never paste paper-table recall numbers into metrics files.
