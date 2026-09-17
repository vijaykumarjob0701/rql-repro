# Synthetic Gaussian fixtures

**Date:** 2026-09-17 (Europe/Dublin)

Regenerable float32 Gaussian matrices for offline / CI smoke. **Not** a substitute for SIFT1M P0.

```bash
python datasets/synthetic/generate_gaussian.py --n 128 --d 8 --seed 42 \
  --out datasets/synthetic/fixtures/tiny
```

Committed under `fixtures/tiny/`: small `.npz.gz` (and optional `.npy`) only.
