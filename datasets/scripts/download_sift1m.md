# Download SIFT1M (instructions only — no binary)

**Date:** 2026-09-17 (Europe/Dublin)  
**Do not** commit the downloaded files to git.

## 1. Accept terms

Review the TexMex / IRISA corpus terms at http://corpus-texmex.irisa.fr/ before downloading.

## 2. Fetch

Typical ANN_SIFT1M artifacts (URLs may redirect; verify on the corpus page):

```bash
mkdir -p datasets/data/sift1m
cd datasets/data/sift1m

# Example pattern — confirm exact filenames on the corpus site:
# wget http://corpus-texmex.irisa.fr/sift/sift.tar.gz
# tar xf sift.tar.gz
```

You should end up with `.fvecs` / `.ivecs` for base, learn, query, and groundtruth.

## 3. Record digests

```bash
sha256sum sift_*.fvecs sift_*.ivecs 2>/dev/null || sha256sum *
```

Paste the hex digests into [`../REGISTRY.md`](../REGISTRY.md) (replace `TBD — fill after download`). **Do not invent digests.**

## 4. Use

Point FANNS harness / Colab cells at `datasets/data/sift1m/`. Commit only `ENV.txt`, `metrics.json`, and plans under `results/` — never the vectors.
