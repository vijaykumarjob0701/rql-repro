#!/usr/bin/env python3
"""Deterministic Reciprocal Rank Fusion on fixed lists (Cormack et al. 2009).

Reports only computed rankings for toy inputs — not an IR benchmark.
Formula: RRFscore(d) = sum_r 1/(k + r(d)), ranks 1-based, default k=60.
"""
from __future__ import annotations

from collections import defaultdict


def rrf(*rankings: list[str], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def main() -> int:
    dense = ["D1", "D2", "D3", "D4"]
    bm25 = ["D3", "D1", "D5", "D2"]
    fused = rrf(dense, bm25, k=60)
    print("RRF unit test (k=60)")
    print("dense:", dense)
    print("bm25:", bm25)
    print("fused:")
    for doc, score in fused:
        print(f"  {doc}\t{score:.6f}")
    # Deterministic assertions (toy gold)
    assert fused[0][0] == "D1"
    assert fused[1][0] == "D3"
    print("OK: top-2 are D1, D3 as expected for this toy input")

    # Property: channel-order invariance of scores (Cormack sum is commutative)
    fused_swap = rrf(bm25, dense, k=60)
    assert [d for d, _ in fused] == [d for d, _ in fused_swap]
    for (d1, s1), (d2, s2) in zip(fused, fused_swap):
        assert d1 == d2 and abs(s1 - s2) < 1e-12
    print("OK: property channel-order invariance (scores identical)")

    # Property: explicit k=60 score for D1 = 1/(60+1) + 1/(60+2)
    expected_d1 = 1.0 / (60 + 1) + 1.0 / (60 + 2)
    got_d1 = dict(fused)["D1"]
    assert abs(got_d1 - expected_d1) < 1e-12
    print(f"OK: property D1 score matches Cormack formula ({got_d1:.6f})")

    # Property: larger k dampens early-rank gaps (same lists; top doc score shrinks toward 2/k)
    s60 = dict(rrf(dense, bm25, k=60))["D1"]
    s500 = dict(rrf(dense, bm25, k=500))["D1"]
    assert s500 < s60
    print("OK: property larger k reduces absolute RRF scores (damping)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
