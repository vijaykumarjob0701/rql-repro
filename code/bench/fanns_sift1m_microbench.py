#!/usr/bin/env python3
"""FANNS SIFT1M microbench — PRE/POST filtered search on TexMex SIFT1M.

Default: subset smoke (first 100k base + 100 queries) for quick plumbing.
Optional --full attempts N=1e6 (memory-heavy; may skip on OOM).

Label subset runs clearly. Not a substitute for venue-grade P0 until full
licensed set + reported ENV are reviewed. Does not paste paper numbers.

Date: 2026-09-17 Europe/Dublin.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = REPO_ROOT / "datasets" / "cache" / "sift1m"
DEFAULT_OUT_PARENT = REPO_ROOT / "results" / "fanns"
# Companion research copy (best-effort)
RESEARCH_COPY = Path("/workspace/rag-vector-query-lang/experiments/results/fanns")

SELECTIVITIES = (0.01, 0.05, 0.1, 0.5)
K = 10
SEED = 42


def _now_dublin() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def _run_id(kind: str) -> str:
    return f"sift1m_{kind}_{_now_dublin().strftime('%Y%m%d_%H%M%S')}"


def read_fvecs(path: Path, max_n: int | None = None) -> np.ndarray:
    """Load .fvecs (int32 dim + float32[dim]) into float32 (n, d)."""
    path = Path(path)
    x = np.memmap(path, dtype=np.int32, mode="r")
    if x.size < 1:
        raise ValueError(f"empty fvecs: {path}")
    d = int(x[0])
    assert d > 0
    n_total = x.size // (d + 1)
    n = n_total if max_n is None else min(n_total, max_n)
    block = np.array(x[: n * (d + 1)], dtype=np.int32, copy=True).reshape(n, d + 1)
    if not np.all(block[:, 0] == d):
        raise ValueError(f"inconsistent dim in {path}")
    return block[:, 1:].copy().view(np.float32).reshape(n, d).copy()


def read_ivecs(path: Path, max_n: int | None = None) -> np.ndarray:
    path = Path(path)
    x = np.memmap(path, dtype=np.int32, mode="r")
    d = int(x[0])
    n_total = x.size // (d + 1)
    n = n_total if max_n is None else min(n_total, max_n)
    block = np.array(x[: n * (d + 1)], dtype=np.int32, copy=True).reshape(n, d + 1)
    return np.ascontiguousarray(block[:, 1:])


def l2_normalize(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n = np.maximum(n, 1e-12)
    return (x / n).astype(np.float32, copy=False)


def brute_topk(db: np.ndarray, queries: np.ndarray, k: int) -> np.ndarray:
    """Nearest neighbors by L2 on (optionally) unit vectors → max IP."""
    sims = queries @ db.T
    k = min(k, db.shape[0])
    part = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
    rows = np.arange(queries.shape[0])[:, None]
    top_sims = sims[rows, part]
    order = np.argsort(-top_sims, axis=1)
    return part[rows, order]


def recall_at_k(pred: np.ndarray, truth: np.ndarray) -> float:
    nq, k = pred.shape
    hits = 0
    for i in range(nq):
        tset = {int(x) for x in truth[i].tolist() if int(x) >= 0}
        pset = {int(x) for x in pred[i].tolist() if int(x) >= 0}
        hits += len(pset & tset)
    return hits / (nq * k) if nq and k else 0.0


def filtered_gt(db: np.ndarray, queries: np.ndarray, mask: np.ndarray, k: int) -> np.ndarray:
    ids = np.flatnonzero(mask)
    out = np.full((queries.shape[0], k), -1, dtype=np.int64)
    if ids.size == 0:
        return out
    local = brute_topk(db[ids], queries, min(k, ids.size))
    mapped = ids[local]
    out[:, : mapped.shape[1]] = mapped
    return out


def post_filter_search(
    db: np.ndarray,
    queries: np.ndarray,
    mask: np.ndarray,
    k: int,
    candidate_mult: int = 50,
) -> tuple[np.ndarray, list[float]]:
    n = db.shape[0]
    cand_k = min(n, max(k * candidate_mult, k))
    times: list[float] = []
    out = np.full((queries.shape[0], k), -1, dtype=np.int64)
    for i in range(queries.shape[0]):
        t0 = time.perf_counter()
        cands = brute_topk(db, queries[i : i + 1], cand_k)[0]
        kept = [int(c) for c in cands if mask[c]]
        if len(kept) < k:
            ids = np.flatnonzero(mask)
            if ids.size:
                sub_rank = brute_topk(db[ids], queries[i : i + 1], min(k, ids.size))[0]
                for j in ids[sub_rank]:
                    if int(j) not in kept:
                        kept.append(int(j))
                    if len(kept) >= k:
                        break
        out[i, : min(k, len(kept))] = kept[:k]
        times.append((time.perf_counter() - t0) * 1000.0)
    return out, times


def pre_filter_search(
    db: np.ndarray, queries: np.ndarray, mask: np.ndarray, k: int
) -> tuple[np.ndarray, list[float]]:
    ids = np.flatnonzero(mask)
    times: list[float] = []
    out = np.full((queries.shape[0], k), -1, dtype=np.int64)
    if ids.size == 0:
        return out, [0.0] * queries.shape[0]
    sub = db[ids]
    for i in range(queries.shape[0]):
        t0 = time.perf_counter()
        local = brute_topk(sub, queries[i : i + 1], min(k, sub.shape[0]))[0]
        out[i, : local.shape[0]] = ids[local]
        times.append((time.perf_counter() - t0) * 1000.0)
    return out, times


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    return float(np.percentile(np.asarray(xs, dtype=np.float64), p))


def run_bench(
    db: np.ndarray,
    queries: np.ndarray,
    *,
    run_id: str,
    label: str,
    dataset_desc: str,
    out_dir: Path,
    nq: int,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plans").mkdir(exist_ok=True)

    rng = np.random.default_rng(SEED)
    n = db.shape[0]
    labels = rng.random(n)
    rows = []
    for s in SELECTIVITIES:
        mask = labels < s
        if int(mask.sum()) < K:
            need = K - int(mask.sum())
            zeros = np.flatnonzero(~mask)
            mask[zeros[:need]] = True
        gt = filtered_gt(db, queries, mask, K)
        for mode, fn in (("PRE", pre_filter_search), ("POST", post_filter_search)):
            if mode == "PRE":
                pred, times = fn(db, queries, mask, K)
            else:
                pred, times = fn(db, queries, mask, K, candidate_mult=50)
            rec = recall_at_k(pred, gt)
            mean_ms = statistics.mean(times) if times else 0.0
            rows.append(
                {
                    "selectivity": s,
                    "mode": mode,
                    "recall_at_10": round(rec, 6),
                    "latency_p50_ms": round(percentile(times, 50), 4),
                    "latency_p95_ms": round(percentile(times, 95), 4),
                    "qps": round((1000.0 / mean_ms) if mean_ms > 0 else 0.0, 4),
                    "n_queries": nq,
                }
            )

    metrics = {
        "run_id": run_id,
        "label": label,
        "warning": (
            "Filtered PRE/POST microbench on SIFT1M vectors with synthetic Bernoulli "
            "predicates. Subset runs are smoke / not full P0. Do not paste paper numbers."
        ),
        "dataset": dataset_desc,
        "rows": rows,
        "mirror": "huggingface.co/datasets/qbo-odp/sift1m",
        "license_note": "INRIA TexMex / academic ANN eval; HF is redistribution mirror",
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with (out_dir / "metrics.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    env_lines = [
        f"run_id={run_id}",
        f"label={label}",
        f"date_ist={_now_dublin().strftime('%Y-%m-%d %H:%M:%S')} (Europe/Dublin)",
        f"python={sys.version.split()[0]}",
        f"numpy={np.__version__}",
        "ann_backend=numpy_brute (no faiss)",
        f"platform={platform.platform()}",
        f"processor={platform.processor() or 'unknown'}",
        f"n={n} d={db.shape[1]} n_queries={nq} k={K} seed={SEED}",
        f"selectivities={list(SELECTIVITIES)}",
        "modes=PRE,POST",
        "post_candidate_mult=50",
        "dataset_mirror=huggingface.co/datasets/qbo-odp/sift1m",
    ]
    (out_dir / "ENV.txt").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    plan = {
        "command": "python code/bench/fanns_sift1m_microbench.py",
        "seed": SEED,
        "n": n,
        "d": int(db.shape[1]),
        "n_queries": nq,
        "k": K,
        "selectivities": list(SELECTIVITIES),
        "modes": ["PRE", "POST"],
        "post_candidate_mult": 50,
        "label": label,
        "dataset": dataset_desc,
    }
    (out_dir / "plans" / "run.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    scope = "SUBSET" if "subset" in label.lower() else "FULL"
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                f"# {run_id}",
                "",
                f"**Scope: {scope}.** Label: `{label}`.",
                "",
                "PRE/POST filtered microbench on SIFT1M (TexMex via HF `qbo-odp/sift1m`).",
                "Synthetic Bernoulli predicates at selectivities {0.01, 0.05, 0.1, 0.5}.",
                "Official `sift_groundtruth.ivecs` is unfiltered 100-NN; this run recomputes "
                "**filtered** GT on the loaded base subset/full set.",
                "",
                f"- Dataset: `{dataset_desc}`",
                f"- Artifacts: `metrics.json`, `ENV.txt`, `plans/`",
                "- Do **not** treat subset smoke as venue-grade P0 alone.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return out_dir


def copy_to_research(src: Path) -> Path | None:
    if not RESEARCH_COPY.parent.exists():
        return None
    dst = RESEARCH_COPY / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--n-base", type=int, default=100_000, help="subset base size (default 100k)")
    ap.add_argument("--nq", type=int, default=100, help="number of queries (default 100)")
    ap.add_argument("--full", action="store_true", help="also attempt full 1M base after subset")
    ap.add_argument("--skip-subset", action="store_true", help="skip subset; only --full")
    ap.add_argument("--out-parent", type=Path, default=DEFAULT_OUT_PARENT)
    args = ap.parse_args()

    cache = args.cache
    base_path = cache / "sift_base.fvecs"
    query_path = cache / "sift_query.fvecs"
    if not base_path.is_file() or not query_path.is_file():
        print(f"ERROR: missing {base_path} or {query_path}", file=sys.stderr)
        print("Run: bash datasets/scripts/download_sift1m.sh", file=sys.stderr)
        sys.exit(1)

    results: list[Path] = []

    if not args.skip_subset:
        print(f"Loading subset: first {args.n_base} base + {args.nq} queries from {cache}")
        db = l2_normalize(read_fvecs(base_path, max_n=args.n_base))
        queries = l2_normalize(read_fvecs(query_path, max_n=args.nq))
        rid = _run_id("subset")
        label = f"subset smoke (n={db.shape[0]}, nq={queries.shape[0]}) — not full P0"
        desc = (
            f"SIFT1M subset first {db.shape[0]} of base + first {queries.shape[0]} queries; "
            f"d=128; mirror=HF qbo-odp/sift1m"
        )
        out = run_bench(
            db,
            queries,
            run_id=rid,
            label=label,
            dataset_desc=desc,
            out_dir=args.out_parent / rid,
            nq=queries.shape[0],
        )
        print(f"Wrote SUBSET results under {out}")
        copied = copy_to_research(out)
        if copied:
            print(f"Copied to research: {copied}")
        results.append(out)
        # free before optional full
        del db, queries

    if args.full:
        print("Attempting FULL SIFT1M (n=1e6) — may fail on memory")
        try:
            db = l2_normalize(read_fvecs(base_path, max_n=None))
            queries = l2_normalize(read_fvecs(query_path, max_n=args.nq))
            rid = _run_id("full")
            label = f"full SIFT1M (n={db.shape[0]}, nq={queries.shape[0]}) — microbench"
            desc = (
                f"SIFT1M full base N={db.shape[0]} + first {queries.shape[0]} queries; "
                f"d=128; mirror=HF qbo-odp/sift1m"
            )
            out = run_bench(
                db,
                queries,
                run_id=rid,
                label=label,
                dataset_desc=desc,
                out_dir=args.out_parent / rid,
                nq=queries.shape[0],
            )
            print(f"Wrote FULL results under {out}")
            copied = copy_to_research(out)
            if copied:
                print(f"Copied to research: {copied}")
            results.append(out)
        except MemoryError as e:
            print(f"FULL run skipped (MemoryError): {e}", file=sys.stderr)
        except Exception as e:
            print(f"FULL run failed: {e}", file=sys.stderr)
            traceback.print_exc()

    if not results:
        print("No runs completed", file=sys.stderr)
        sys.exit(1)
    print("Done:", ", ".join(str(p) for p in results))


if __name__ == "__main__":
    main()
