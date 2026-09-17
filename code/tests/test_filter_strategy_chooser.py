#!/usr/bin/env python3
"""Deterministic toy FilterExec chooser on fixed synthetic predicates.

Documents a *decision rule only* — not an ANN benchmark and not learned costing.
Modes align with hypothesized RQL FilterExec vocabulary (thesis §06).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

Mode = str  # PRE | POST | ITERATIVE | SUBGRAPH | SPECIALIZED | PARTITION | ROUTER | AUTO-resolved


@dataclass(frozen=True)
class Capabilities:
    subgraph: bool = False
    specialized_labels: bool = False
    ann_iterator: bool = False


@dataclass(frozen=True)
class Stats:
    selectivity: float  # fraction surviving predicate, in (0, 1]
    specificity: float  # Filtered-DiskANN-style: fraction matching label; use 1.0 if N/A
    correlation: str  # "pos" | "neg" | "none" | "unknown"
    predicate_kind: str  # "acl" | "label_eq" | "range" | "complex"
    acl_hard: bool = False


def choose(stats: Stats, caps: Capabilities) -> Mode:
    """Pure function: fixed thresholds for unit-test determinism only."""
    # Hard ACL: never choose a mode that implies client-side-only filtering.
    # Toy rule: always allow server-side modes; prefer ITERATIVE/SUBGRAPH/SPECIALIZED/PRE over POST.
    if stats.acl_hard and stats.predicate_kind == "acl":
        if caps.ann_iterator:
            return "ITERATIVE"
        if caps.subgraph:
            return "SUBGRAPH"
        return "PRE"

    if (
        stats.predicate_kind == "label_eq"
        and caps.specialized_labels
        and stats.specificity <= 0.25
    ):
        return "SPECIALIZED"

    if stats.selectivity <= 0.05 and caps.subgraph:
        return "SUBGRAPH"

    if stats.selectivity <= 0.15 and caps.ann_iterator:
        return "ITERATIVE"

    if stats.selectivity >= 0.5 and stats.correlation in ("pos", "none", "unknown"):
        return "POST"

    if stats.selectivity >= 0.3:
        return "PRE"

    # Fallbacks by capability
    if caps.ann_iterator:
        return "ITERATIVE"
    if caps.subgraph:
        return "SUBGRAPH"
    if caps.specialized_labels and stats.predicate_kind == "label_eq":
        return "SPECIALIZED"
    return "POST"


CASES: list[tuple[str, Stats, Capabilities, Mode]] = [
    (
        "acl_hard_prefers_iterator",
        Stats(0.2, 1.0, "unknown", "acl", acl_hard=True),
        Capabilities(ann_iterator=True, subgraph=True),
        "ITERATIVE",
    ),
    (
        "low_specificity_label_specialized",
        Stats(0.4, 0.01, "none", "label_eq"),
        Capabilities(specialized_labels=True),
        "SPECIALIZED",
    ),
    (
        "very_low_selectivity_subgraph",
        Stats(0.02, 1.0, "neg", "complex"),
        Capabilities(subgraph=True, ann_iterator=True),
        "SUBGRAPH",
    ),
    (
        "mid_low_selectivity_iterator",
        Stats(0.10, 1.0, "neg", "range"),
        Capabilities(ann_iterator=True),
        "ITERATIVE",
    ),
    (
        "high_selectivity_post",
        Stats(0.8, 1.0, "pos", "complex"),
        Capabilities(),
        "POST",
    ),
    (
        "mid_selectivity_pre",
        Stats(0.4, 1.0, "none", "range"),
        Capabilities(),
        "PRE",
    ),
]


def main() -> int:
    lines = [
        "FilterExec strategy chooser unit test (deterministic toy thresholds)",
        "NOT an ANN benchmark; documents decision rule only.",
        "",
    ]
    for name, stats, caps, expected in CASES:
        got = choose(stats, caps)
        ok = got == expected
        lines.append(
            f"{name}: got={got} expected={expected} {'OK' if ok else 'FAIL'}"
        )
        assert ok, f"{name}: {got} != {expected}"
    lines.append("")
    lines.append(f"OK: {len(CASES)} cases passed")
    text = "\n".join(lines) + "\n"
    out = Path(__file__).resolve().parents[2] / "results" / "scratch" / "filter_chooser" / "unit_test.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text, end="")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
