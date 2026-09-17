#!/usr/bin/env python3
"""Regenerate tiny synthetic Gaussian vector fixtures (offline / CI).

Not a P0 ANN benchmark dataset. Writes small .npy and .npz.gz under --out.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=128, help="number of vectors")
    ap.add_argument("--d", type=int, default=8, help="dimension")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "fixtures" / "tiny",
        help="output directory",
    )
    ap.add_argument("--nq", type=int, default=8, help="number of query vectors")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    base = rng.standard_normal((args.n, args.d), dtype=np.float32)
    queries = rng.standard_normal((args.nq, args.d), dtype=np.float32)

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    base_npy = out / f"base_n{args.n}_d{args.d}_s{args.seed}.npy"
    query_npy = out / f"query_nq{args.nq}_d{args.d}_s{args.seed}.npy"
    np.save(base_npy, base)
    np.save(query_npy, queries)

    base_gz = out / f"base_n{args.n}_d{args.d}_s{args.seed}.npz.gz"
    query_gz = out / f"query_nq{args.nq}_d{args.d}_s{args.seed}.npz.gz"
    with gzip.open(base_gz, "wb") as f:
        np.save(f, base)
    with gzip.open(query_gz, "wb") as f:
        np.save(f, queries)

    meta = {
        "kind": "synthetic_gaussian",
        "n": args.n,
        "d": args.d,
        "nq": args.nq,
        "seed": args.seed,
        "dtype": "float32",
        "files": [base_npy.name, query_npy.name, base_gz.name, query_gz.name],
        "not_p0": True,
    }
    (out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({args.n}x{args.d}, seed={args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
