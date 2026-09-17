#!/usr/bin/env python3
"""FANNS SIFT1M FAISS-index filtered-ANN microbench (protocol 01 aligned).

Primary index: HNSW32 (M=32). Rationale vs IVF4096,Flat:
  - No training / nlist / nprobe tuning for a first venue-style curve.
  - Graph indexes are the usual filtered-ANN literature baseline family.
  - FAISS SearchParametersHNSW + IDSelectorBitmap gives clean PRE filtering.
  - efSearch is a single candidate-depth knob (recorded in ENV).

Modes:
  POST — HNSW search top-(k*mult), then keep predicate-true ids.
         No exact Flat pad; <k survivors → shortfall (honest POST).
  PRE  — same HNSW index with IDSelectorBitmap over predicate-true ids.

Filtered GT: exact L2 via IndexFlatL2 + IDSelectorBitmap on the same base
(not official unfiltered sift_groundtruth.ivecs).

Predicates: same Bernoulli seed=42 as fanns_sift1m_microbench.py (labels < s).

Date: 2026-09-17 Europe/Dublin. Real metrics only — not ACORN numbers.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = REPO_ROOT / "datasets" / "cache" / "sift1m"
DEFAULT_OUT_PARENT = REPO_ROOT / "results" / "fanns"
RESEARCH_COPY = Path("/workspace/rag-vector-query-lang/experiments/results/fanns")

SELECTIVITIES = (0.01, 0.05, 0.1, 0.5)
K = 10
SEED = 42
INDEX_KEY = "HNSW32"
HNSW_M = 32
EF_CONSTRUCTION = 200
EF_SEARCH = 64
POST_CAND_MULT = 50


def _now_dublin() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def _run_id() -> str:
    return f"sift1m_faiss_{INDEX_KEY}_{_now_dublin().strftime('%Y%m%d_%H%M%S')}"


def read_fvecs(path: Path, max_n: int | None = None) -> np.ndarray:
    path = Path(path)
    x = np.memmap(path, dtype=np.int32, mode="r")
    if x.size < 1:
        raise ValueError(f"empty fvecs: {path}")
    d = int(x[0])
    n_total = x.size // (d + 1)
    n = n_total if max_n is None else min(n_total, max_n)
    block = np.array(x[: n * (d + 1)], dtype=np.int32, copy=True).reshape(n, d + 1)
    if not np.all(block[:, 0] == d):
        raise ValueError(f"inconsistent dim in {path}")
    return block[:, 1:].copy().view(np.float32).reshape(n, d).copy()


def recall_at_k(pred: np.ndarray, truth: np.ndarray) -> float:
    nq, k = pred.shape
    hits = 0
    for i in range(nq):
        tset = {int(x) for x in truth[i].tolist() if int(x) >= 0}
        pset = {int(x) for x in pred[i].tolist() if int(x) >= 0}
        hits += len(pset & tset)
    return hits / (nq * k) if nq and k else 0.0


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    return float(np.percentile(np.asarray(xs, dtype=np.float64), p))


def make_mask(n: int, s: float, rng: np.random.Generator) -> np.ndarray:
    """Bernoulli predicate on ids (same convention as NumPy microbench)."""
    labels = rng.random(n)
    mask = labels < s
    if int(mask.sum()) < K:
        need = K - int(mask.sum())
        zeros = np.flatnonzero(~mask)
        mask[zeros[:need]] = True
    return mask


def mask_to_bitmap(mask: np.ndarray):
    """Return (selector, bits_buffer). Caller MUST keep bits_buffer alive while sel is used."""
    import faiss

    n = int(mask.shape[0])
    nbytes = (n + 7) // 8
    bits = np.packbits(mask.astype(np.uint8), bitorder="little")
    if bits.size < nbytes:
        bits = np.pad(bits, (0, nbytes - bits.size))
    bits = np.ascontiguousarray(bits[:nbytes].copy())
    sel = faiss.IDSelectorBitmap(n, faiss.swig_ptr(bits))
    return sel, bits


def filtered_gt_flat(flat, queries: np.ndarray, mask: np.ndarray, k: int) -> np.ndarray:
    import faiss

    nq = queries.shape[0]
    out = np.full((nq, k), -1, dtype=np.int64)
    sel, bits = mask_to_bitmap(mask)
    params = faiss.SearchParameters()
    params.sel = sel
    _D, I = flat.search(queries, k, params=params)
    _ = bits  # IDSelectorBitmap holds raw ptr into bits; keep through search
    for i in range(nq):
        row = [int(idx) for idx in I[i].tolist() if int(idx) >= 0]
        out[i, : len(row)] = row[:k]
    return out


def build_hnsw(xb: np.ndarray):
    import faiss

    d = xb.shape[1]
    # OpenMP multi-thread add (IndexHNSWFlat has no public seed). Record omp in ENV.
    faiss.omp_set_num_threads(faiss.omp_get_max_threads())
    index = faiss.IndexHNSWFlat(d, HNSW_M, faiss.METRIC_L2)
    index.hnsw.efConstruction = EF_CONSTRUCTION
    index.add(xb)
    index.hnsw.efSearch = EF_SEARCH
    return index


def build_flat(xb: np.ndarray):
    import faiss

    index = faiss.IndexFlatL2(xb.shape[1])
    index.add(xb)
    return index


def post_filter_search(index, queries: np.ndarray, mask: np.ndarray, k: int, cand_mult: int):
    """Pure POST: ANN top-(k*mult), then predicate filter. No exact Flat pad."""
    import faiss

    n = mask.shape[0]
    cand_k = min(n, max(k * cand_mult, k))
    times: list[float] = []
    out = np.full((queries.shape[0], k), -1, dtype=np.int64)
    params = faiss.SearchParametersHNSW()
    # efSearch must be >= cand_k for HNSW to actually explore that pool
    params.efSearch = max(EF_SEARCH, cand_k)
    for i in range(queries.shape[0]):
        q = queries[i : i + 1]
        t0 = time.perf_counter()
        _D, I = index.search(q, cand_k, params=params)
        kept: list[int] = []
        for c in I[0].tolist():
            c = int(c)
            if c >= 0 and mask[c]:
                kept.append(c)
            if len(kept) >= k:
                break
        out[i, : min(k, len(kept))] = kept[:k]
        times.append((time.perf_counter() - t0) * 1000.0)
    return out, times


def pre_filter_search(index, queries: np.ndarray, mask: np.ndarray, k: int):
    import faiss

    times: list[float] = []
    out = np.full((queries.shape[0], k), -1, dtype=np.int64)
    sel, bits = mask_to_bitmap(mask)
    params = faiss.SearchParametersHNSW()
    params.efSearch = EF_SEARCH
    params.sel = sel
    for i in range(queries.shape[0]):
        q = queries[i : i + 1]
        t0 = time.perf_counter()
        _D, I = index.search(q, k, params=params)
        row = [int(c) for c in I[0].tolist() if int(c) >= 0]
        out[i, : min(k, len(row))] = row[:k]
        times.append((time.perf_counter() - t0) * 1000.0)
    _ = bits  # lifetime: IDSelectorBitmap holds raw ptr into bits
    return out, times


def copy_to_research(src: Path) -> Path | None:
    if not RESEARCH_COPY.parent.exists():
        return None
    RESEARCH_COPY.mkdir(parents=True, exist_ok=True)
    dst = RESEARCH_COPY / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def run_bench(xb: np.ndarray, queries: np.ndarray, *, out_dir: Path, run_id: str, faiss_ver: str) -> dict:
    import faiss

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plans").mkdir(exist_ok=True)

    n, d = xb.shape
    nq = queries.shape[0]
    print(f"Building Flat GT index on n={n} d={d} …", flush=True)
    t_flat0 = time.perf_counter()
    flat = build_flat(xb)
    print(f"  Flat ready in {time.perf_counter() - t_flat0:.1f}s", flush=True)

    print(f"Building {INDEX_KEY} (M={HNSW_M}, efC={EF_CONSTRUCTION}) …", flush=True)
    t_b0 = time.perf_counter()
    index = build_hnsw(xb)
    build_s = time.perf_counter() - t_b0
    print(f"  HNSW ready in {build_s:.1f}s; ntotal={index.ntotal}", flush=True)

    rng = np.random.default_rng(SEED)
    rows = []
    wall0 = time.perf_counter()

    for s in SELECTIVITIES:
        mask = make_mask(n, s, rng)
        n_true = int(mask.sum())
        print(f"selectivity={s} n_true={n_true} — computing filtered Flat GT …", flush=True)
        t_gt0 = time.perf_counter()
        gt = filtered_gt_flat(flat, queries, mask, K)
        print(f"  GT in {time.perf_counter() - t_gt0:.1f}s", flush=True)

        for mode in ("PRE", "POST"):
            print(f"  mode={mode} …", flush=True)
            if mode == "PRE":
                pred, times = pre_filter_search(index, queries, mask, K)
            else:
                pred, times = post_filter_search(index, queries, mask, K, POST_CAND_MULT)
            rec = recall_at_k(pred, gt)
            mean_ms = statistics.mean(times) if times else 0.0
            row = {
                "selectivity": s,
                "mode": mode,
                "recall_at_10": round(rec, 6),
                "latency_p50_ms": round(percentile(times, 50), 4),
                "latency_p95_ms": round(percentile(times, 95), 4),
                "qps": round((1000.0 / mean_ms) if mean_ms > 0 else 0.0, 4),
                "n_queries": nq,
                "n_predicate_true": n_true,
                "index": INDEX_KEY,
                "efSearch": EF_SEARCH if mode == "PRE" else max(EF_SEARCH, K * POST_CAND_MULT),
                "post_candidate_mult": POST_CAND_MULT if mode == "POST" else None,
            }
            rows.append(row)
            print(
                f"    recall@10={row['recall_at_10']} p50={row['latency_p50_ms']}ms "
                f"p95={row['latency_p95_ms']}ms qps={row['qps']}",
                flush=True,
            )

    wall_s = time.perf_counter() - wall0

    metrics = {
        "run_id": run_id,
        "label": (
            f"FAISS {INDEX_KEY} filtered-ANN microbench on SIFT1M "
            f"(n={n}, nq={nq}) — not ACORN; synthetic predicates"
        ),
        "warning": (
            "Real FAISS-index ANN PRE/POST on SIFT1M with synthetic Bernoulli "
            "predicates (seed=42). Filtered GT = exact FlatL2 + IDSelectorBitmap. "
            "Not ACORN / paper numbers. Not live-adapter or RAG judgments. "
            "Vanilla HNSW+filter recall drops at low selectivity (known; motivates ACORN-class methods)."
        ),
        "dataset": (
            f"SIFT1M full base N={n} + first {nq} queries; d={d}; "
            f"mirror=HF qbo-odp/sift1m; L2 (no normalize — TexMex SIFT convention)"
        ),
        "index": {
            "type": INDEX_KEY,
            "faiss_factory": f"HNSW{HNSW_M}",
            "M": HNSW_M,
            "efConstruction": EF_CONSTRUCTION,
            "efSearch": EF_SEARCH,
            "metric": "L2",
            "why_primary": (
                "HNSW32 chosen over IVF4096,Flat: no train/nprobe tuning; "
                "graph family matches filtered-ANN literature; IDSelectorBitmap "
                "PRE is first-class; efSearch is the depth knob."
            ),
            "build_seconds": round(build_s, 3),
        },
        "gt_method": "IndexFlatL2 + IDSelectorBitmap (exact filtered top-k)",
        "pre_method": "SearchParametersHNSW + IDSelectorBitmap on full HNSW32",
        "post_method": (
            f"HNSW search top-(k*{POST_CAND_MULT}) then predicate filter "
            "(no exact pad; shortfall → -1)"
        ),
        "predicate": "Bernoulli labels=rng(seed=42).random(n) < s (same as NumPy microbench)",
        "rows": rows,
        "wall_seconds_search_and_gt": round(wall_s, 3),
        "mirror": "huggingface.co/datasets/qbo-odp/sift1m",
        "license_note": "INRIA TexMex / academic ANN eval; HF is redistribution mirror",
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with (out_dir / "metrics.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    cpu = "unknown"
    try:
        cpu = (
            open("/proc/cpuinfo", encoding="utf-8")
            .read()
            .split("model name")[1]
            .split(":")[1]
            .split("\n")[0]
            .strip()
        )
    except Exception:
        cpu = platform.processor() or platform.machine()

    env_lines = [
        f"run_id={run_id}",
        f"date_ist={_now_dublin().strftime('%Y-%m-%d %H:%M:%S')} (Europe/Dublin)",
        f"python={sys.version.split()[0]}",
        f"numpy={np.__version__}",
        f"faiss={faiss_ver}",
        f"ann_backend=faiss-cpu IndexHNSWFlat M={HNSW_M}",
        f"index_string={INDEX_KEY}",
        f"efConstruction={EF_CONSTRUCTION}",
        f"efSearch={EF_SEARCH}",
        f"nprobe=n/a (HNSW)",
        f"post_candidate_mult={POST_CAND_MULT}",
        f"metric=L2",
        f"platform={platform.platform()}",
        f"cpu={cpu}",
        f"omp_threads_search={faiss.omp_get_max_threads()}",
        "omp_threads_hnsw_build=omp_max (multi)",
        f"n={n} d={d} n_queries={nq} k={K} seed={SEED}",
        f"selectivities={list(SELECTIVITIES)}",
        "modes=PRE,POST",
        "gt=IndexFlatL2+IDSelectorBitmap",
        "pre=SearchParametersHNSW+IDSelectorBitmap",
        "post=HNSW top-(k*mult) then filter (no exact pad)",
        "dataset_mirror=huggingface.co/datasets/qbo-odp/sift1m",
        f"index_build_seconds={build_s:.3f}",
        f"wall_seconds_search_and_gt={wall_s:.3f}",
    ]
    (out_dir / "ENV.txt").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    plan = {
        "command": "python code/bench/fanns_sift1m_faiss_microbench.py",
        "seed": SEED,
        "n": n,
        "d": d,
        "n_queries": nq,
        "k": K,
        "selectivities": list(SELECTIVITIES),
        "modes": ["PRE", "POST"],
        "index": INDEX_KEY,
        "M": HNSW_M,
        "efConstruction": EF_CONSTRUCTION,
        "efSearch": EF_SEARCH,
        "post_candidate_mult": POST_CAND_MULT,
        "gt_method": "IndexFlatL2 + IDSelectorBitmap",
        "pre_method": "SearchParametersHNSW + IDSelectorBitmap",
        "post_method": "HNSW top-(k*mult) then filter (no exact pad)",
        "predicate": "Bernoulli seed=42",
        "why_hnsw": metrics["index"]["why_primary"],
    }
    (out_dir / "plans" / "run.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    (out_dir / "README.md").write_text(
        "\n".join(
            [
                f"# {run_id}",
                "",
                "**FAISS-index ANN microbench on SIFT1M** (stronger than brute NumPy).",
                "",
                f"- Index: **{INDEX_KEY}** (`IndexHNSWFlat`, M={HNSW_M}, efConstruction={EF_CONSTRUCTION}, efSearch={EF_SEARCH})",
                "- Why HNSW32 (not IVF4096,Flat): no train/nprobe tuning; graph family; IDSelector PRE; efSearch depth knob.",
                f"- Base: N={n}, d={d}; queries: nq={nq}; k={K}; seed={SEED}",
                f"- Selectivities: {list(SELECTIVITIES)}; modes PRE / POST",
                "- Predicates: synthetic Bernoulli on ids (seed=42) — **not** real metadata attributes",
                "- Filtered GT: exact `IndexFlatL2` + `IDSelectorBitmap` (not official unfiltered `sift_groundtruth.ivecs`)",
                "- PRE: `SearchParametersHNSW` + `IDSelectorBitmap` on the full HNSW index",
                f"- POST: HNSW search top-(k×{POST_CAND_MULT}) then predicate filter (no exact pad; <k survivors → shortfall)",
                "",
                "## Caveats",
                "",
                "- **Not** ACORN (or any paper) numbers — do not compare tables as reproduction.",
                "- Synthetic predicates; single efSearch / candidate-mult setting (not a full depth sweep).",
                "- Vanilla HNSW+filter recall drops at low selectivity (expected; motivates predicate-aware graph methods).",
                "- Still missing live adapters / RAG judgments for venue-complete story.",
                "- L2 on raw SIFT floats (TexMex convention); no L2-normalize.",
                "",
                "Artifacts: `metrics.json`, `metrics.jsonl`, `ENV.txt`, `plans/run.json`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--nq", type=int, default=1000, help="queries (default 1000)")
    ap.add_argument("--out-parent", type=Path, default=DEFAULT_OUT_PARENT)
    args = ap.parse_args()

    try:
        import faiss
    except ImportError:
        print("ERROR: faiss not installed. pip install faiss-cpu", file=sys.stderr)
        sys.exit(1)

    faiss_ver = getattr(faiss, "__version__", "unknown")
    base_path = args.cache / "sift_base.fvecs"
    query_path = args.cache / "sift_query.fvecs"
    if not base_path.is_file() or not query_path.is_file():
        print(f"ERROR: missing {base_path} or {query_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading full SIFT1M base + first {args.nq} queries from {args.cache}", flush=True)
    t0 = time.perf_counter()
    xb = read_fvecs(base_path, max_n=None)
    queries = read_fvecs(query_path, max_n=args.nq)
    print(
        f"Loaded xb={xb.shape} queries={queries.shape} in {time.perf_counter() - t0:.1f}s",
        flush=True,
    )

    rid = _run_id()
    out = args.out_parent / rid
    wall_all0 = time.perf_counter()
    metrics = run_bench(xb, queries, out_dir=out, run_id=rid, faiss_ver=faiss_ver)
    wall_all = time.perf_counter() - wall_all0
    (out / "WALL_TIME.txt").write_text(
        f"wall_seconds_total={wall_all:.3f}\n"
        f"date_ist={_now_dublin().strftime('%Y-%m-%d %H:%M:%S')} (Europe/Dublin)\n",
        encoding="utf-8",
    )
    print(f"Wrote results under {out} (total wall {wall_all:.1f}s)", flush=True)
    copied = copy_to_research(out)
    if copied:
        print(f"Copied to research: {copied}", flush=True)
    print("Done.", flush=True)
    print("\nselectivity mode recall@10 p50_ms p95_ms qps", flush=True)
    for r in metrics["rows"]:
        print(
            f"{r['selectivity']:>5} {r['mode']:<4} {r['recall_at_10']:.4f} "
            f"{r['latency_p50_ms']:.3f} {r['latency_p95_ms']:.3f} {r['qps']:.2f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
