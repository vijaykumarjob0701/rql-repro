#!/usr/bin/env python3
"""Deterministic weighted linear (convex) fusion on fixed channel scores (Bruch-style).

Reports only computed rankings for toy inputs — not an IR benchmark.
Formula: f = alpha * phi(sem) + (1 - alpha) * phi(lex) with min-max phi over the
candidate union (Bruch Eqs. 2–3; identity / theoretical-min variants included).
"""
from __future__ import annotations


def minmax(scores: dict[str, float]) -> dict[str, float]:
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {d: 0.0 for d in scores}
    return {d: (s - lo) / (hi - lo) for d, s in scores.items()}


def theoretical_minmax(scores: dict[str, float], inf: float) -> dict[str, float]:
    """phi_tmm with known theoretical infimum (Bruch Eq. 4)."""
    vals = list(scores.values())
    hi = max(vals)
    denom = hi - inf
    if denom == 0:
        return {d: 0.0 for d in scores}
    return {d: (s - inf) / denom for d, s in scores.items()}


def fuse_linear(
    lex: dict[str, float],
    sem: dict[str, float],
    *,
    alpha: float,
    norm: str = "minmax",
    lex_inf: float = 0.0,
    sem_inf: float = -1.0,
) -> list[tuple[str, float]]:
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    docs = sorted(set(lex) | set(sem))
    # Missing channel score -> channel minimum among present (conservative fill)
    lex_fill = {d: lex.get(d, min(lex.values())) for d in docs}
    sem_fill = {d: sem.get(d, min(sem.values())) for d in docs}
    if norm == "minmax":
        pl, ps = minmax(lex_fill), minmax(sem_fill)
    elif norm == "tmm":
        pl = theoretical_minmax(lex_fill, lex_inf)
        ps = theoretical_minmax(sem_fill, sem_inf)
    elif norm == "identity":
        pl, ps = lex_fill, sem_fill
    else:
        raise ValueError(f"unknown norm: {norm}")
    fused = {d: alpha * ps[d] + (1.0 - alpha) * pl[d] for d in docs}
    return sorted(fused.items(), key=lambda x: (-x[1], x[0]))


def main() -> int:
    # Toy calibrated scores (not a benchmark)
    lex = {"D1": 12.0, "D2": 8.0, "D3": 15.0, "D4": 3.0}  # BM25-like
    sem = {"D1": 0.82, "D2": 0.91, "D3": 0.55, "D4": 0.40}  # cosine-like in [-1,1]

    print("Linear/CC unit test (Bruch-style convex combination)")
    print("lex:", lex)
    print("sem:", sem)

    for alpha in (0.0, 0.5, 0.8, 1.0):
        fused = fuse_linear(lex, sem, alpha=alpha, norm="minmax")
        print(f"fused alpha={alpha} minmax:")
        for doc, score in fused:
            print(f"  {doc}\t{score:.6f}")

    # alpha=0 -> pure lexical order after minmax
    order0 = [d for d, _ in fuse_linear(lex, sem, alpha=0.0, norm="minmax")]
    assert order0[0] == "D3"  # highest lex
    print("OK: alpha=0 prefers highest lexical (D3)")

    # alpha=1 -> pure semantic order after minmax
    order1 = [d for d, _ in fuse_linear(lex, sem, alpha=1.0, norm="minmax")]
    assert order1[0] == "D2"  # highest sem
    print("OK: alpha=1 prefers highest semantic (D2)")

    # alpha=0.8 on this toy: D1 should beat D4 (both mid); exact top is data-dependent
    fused08 = fuse_linear(lex, sem, alpha=0.8, norm="minmax")
    scores08 = dict(fused08)
    assert scores08["D1"] > scores08["D4"]
    print("OK: alpha=0.8 keeps D1 above D4 on this toy")

    # Property: convex combination is affine in alpha for fixed normalized scores
    pl, ps = minmax({**{d: lex[d] for d in lex}}), minmax({**{d: sem[d] for d in sem}})
    # Same doc universe
    docs = sorted(set(lex) | set(sem))
    pl = minmax({d: lex.get(d, min(lex.values())) for d in docs})
    ps = minmax({d: sem.get(d, min(sem.values())) for d in docs})
    for d in docs:
        s0 = dict(fuse_linear(lex, sem, alpha=0.0, norm="minmax"))[d]
        s1 = dict(fuse_linear(lex, sem, alpha=1.0, norm="minmax"))[d]
        s05 = dict(fuse_linear(lex, sem, alpha=0.5, norm="minmax"))[d]
        assert abs(s05 - (0.5 * s1 + 0.5 * s0)) < 1e-12
        assert abs(s0 - pl[d]) < 1e-12 and abs(s1 - ps[d]) < 1e-12
    print("OK: property score is affine in alpha under fixed min-max norms")

    # tmm with known infima produces finite scores in [0,1] for this toy
    fused_tmm = fuse_linear(lex, sem, alpha=0.8, norm="tmm", lex_inf=0.0, sem_inf=-1.0)
    for _, s in fused_tmm:
        assert 0.0 <= s <= 1.0 + 1e-12
    print("OK: property tmm scores stay in [0,1] for this toy")

    # identity can put channels on incompatible scales — still deterministic
    fused_id = fuse_linear(lex, sem, alpha=0.5, norm="identity")
    assert len(fused_id) == 4
    print("OK: identity norm runs (scale mismatch intentional; Bruch warns)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
