#!/usr/bin/env python3
"""Deterministic MaxSim late-interaction score on fixed toy embeddings.

Implements ColBERT Eq. (3) (Khattab & Zaharia, SIGIR'20):
  S(q,d) = sum_i max_j <e_q_i, e_d_j>
for L2-normalized vectors (dot = cosine).

Reports only computed scores for toy inputs — not an IR benchmark.
"""
from __future__ import annotations

import math


def l2_normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    assert n > 0
    return [x / n for x in v]


def maxsim(eq: list[list[float]], ed: list[list[float]]) -> float:
    """Sum of per-query-embedding max dot-products against document bag."""
    if not ed:
        raise ValueError("document embedding bag must be non-empty")
    if not eq:
        raise ValueError("query embedding bag must be non-empty")
    total = 0.0
    for qv in eq:
        best = max(sum(a * b for a, b in zip(qv, dv)) for dv in ed)
        total += best
    return total


def main() -> int:
    # Fixed raw vectors → normalize (matches ColBERT cosine-via-L2-norm path)
    eq_raw = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    ed_a_raw = [
        [1.0, 0.0, 0.0],  # matches q0 perfectly
        [0.0, 0.5, 0.0],  # partial match for q1
        [0.0, 0.0, 1.0],
    ]
    ed_b_raw = [
        [0.0, 0.0, 1.0],
        [0.2, 0.2, 0.2],
    ]

    eq = [l2_normalize(v) for v in eq_raw]
    ed_a = [l2_normalize(v) for v in ed_a_raw]
    ed_b = [l2_normalize(v) for v in ed_b_raw]

    s_a = maxsim(eq, ed_a)
    s_b = maxsim(eq, ed_b)

    print("MaxSim unit test (ColBERT Eq.3, L2-normalized dots)")
    print("eq (2 embeddings × 3 dim):", eq)
    print("ed_a:", ed_a)
    print("ed_b:", ed_b)
    print(f"S(q, a) = {s_a:.6f}")
    print(f"S(q, b) = {s_b:.6f}")

    # Hand-derived gold:
    # q0=[1,0,0]: max with ed_a = 1.0 (first doc emb)
    # q1=[0,1,0]: max with ed_a = 1.0 (second doc emb after norm is [0,1,0])
    # → S(q,a) = 2.0
    assert abs(s_a - 2.0) < 1e-9
    print("OK: S(q,a) == 2.0 (exact MaxSim on aligned axes)")

    assert s_a > s_b
    print("OK: property doc a ranks above doc b for this toy query")

    # Property: adding a zero-contribution doc embedding does not change score
    ed_a_extra = ed_a + [l2_normalize([0.0, 0.0, 1.0])]
    s_a2 = maxsim(eq, ed_a_extra)
    assert abs(s_a2 - s_a) < 1e-12
    print("OK: property extra orthogonal doc emb does not change MaxSim here")

    # Property: empty document bag is undefined / rejected
    try:
        maxsim(eq, [])
        raise AssertionError("expected empty doc bag to fail")
    except ValueError:
        print("OK: empty document bag raises ValueError (no silent zero)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
