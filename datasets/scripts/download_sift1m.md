# Download SIFT1M (instructions + script)

**Date:** 2026-09-17 (Europe/Dublin)  
**Do not** commit the downloaded files to git (path is gitignored: `datasets/cache/`).

## License / terms

- Original corpus: **INRIA TexMex** (academic ANN evaluation). Review terms at http://corpus-texmex.irisa.fr/ / IRISA before use.
- Preferred HTTPS mirror: Hugging Face dataset [`qbo-odp/sift1m`](https://huggingface.co/datasets/qbo-odp/sift1m) — **redistribution mirror** of the TexMex `.fvecs`/`.ivecs` files.
- Digests in [`../REGISTRY.md`](../REGISTRY.md) were filled from a verified HF download on 2026-09-17.

## Preferred: Hugging Face HTTPS

```bash
mkdir -p datasets/cache/sift1m
cd datasets/cache/sift1m

BASE=https://huggingface.co/datasets/qbo-odp/sift1m/resolve/main
curl -L -o sift_base.fvecs        "$BASE/sift_base.fvecs"
curl -L -o sift_query.fvecs       "$BASE/sift_query.fvecs"
curl -L -o sift_groundtruth.ivecs "$BASE/sift_groundtruth.ivecs"
# optional:
curl -L -o sift_learn.fvecs       "$BASE/sift_learn.fvecs"
```

Or run the helper (HF first, then FTP):

```bash
bash datasets/scripts/download_sift1m.sh
```

## Fallback: IRISA FTP tarball (~168MB)

```bash
mkdir -p datasets/cache/sift1m
cd datasets/cache/sift1m
curl -L -o sift.tar.gz ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz
tar xf sift.tar.gz
# expect sift/ or flat sift_*.fvecs depending on archive layout — move into this dir
```

## Alternate: ANN-Benchmarks HDF5 (~525MB)

```bash
# Different format — not interchangeable with fvecs loaders without conversion
curl -L -o sift-128-euclidean.hdf5 http://ann-benchmarks.com/sift-128-euclidean.hdf5
```

## Dead: TexMex HTTPS (do not use)

As of 2026-09-17, `https://corpus-texmex.irisa.fr/sift.tar.gz` fails (SSL certificate hostname mismatch / 404). Prefer HF or FTP.

## Record digests

```bash
cd datasets/cache/sift1m
sha256sum sift_*.fvecs sift_*.ivecs | tee SHA256SUMS
```

Compare against [`../REGISTRY.md`](../REGISTRY.md). **Do not invent digests.**

## Use

Point FANNS harness / Colab at `datasets/cache/sift1m/`. Commit only `ENV.txt`, `metrics.json`, and plans under `results/` — never the vectors.
