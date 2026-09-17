"""Pytest wrappers around offline RQL smokes (no live DBs)."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


def _run_script(name: str) -> None:
    path = TESTS / name
    # Scripts use SystemExit; catch and assert 0
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        assert code == 0, f"{name} exited {e.code}"


def test_rrf_fusion() -> None:
    _run_script("test_rrf_fusion.py")


def test_maxsim_late() -> None:
    _run_script("test_maxsim_late.py")


def test_linear_fusion() -> None:
    _run_script("test_linear_fusion.py")


def test_filter_strategy_chooser() -> None:
    _run_script("test_filter_strategy_chooser.py")


def test_rql_parser() -> None:
    _run_script("test_rql_parser.py")


def test_validate_plans() -> None:
    _run_script("validate_plans.py")


def test_rql_planner_depends_on_parser() -> None:
    # Planner reads logical JSON produced by parser into results/scratch/
    _run_script("test_rql_parser.py")
    _run_script("test_rql_planner.py")


def test_rql_adapters_depends_on_planner() -> None:
    _run_script("test_rql_parser.py")
    _run_script("test_rql_planner.py")
    _run_script("test_rql_adapters.py")


def test_pipeline_e2e_import_and_parse() -> None:
    from rql_parser.parser import parse_rql_file
    from rql_planner.planner import load_profile, plan_logical
    from rql_adapters.emit import emit_plan

    toy = CODE / "examples" / "toy" / "01-hybrid-rrf.rql"
    logical = parse_rql_file(toy)
    assert logical["root"]["op"]
    physical = plan_logical(logical, load_profile("qdrant"), logical_ref=str(toy))
    art = emit_plan(physical)
    assert art.get("vendor") == "qdrant"


def test_tiny_fixture_manifest_exists() -> None:
    root = CODE.parent
    manifest = root / "datasets" / "synthetic" / "fixtures" / "tiny" / "manifest.json"
    assert manifest.is_file(), "run generate_gaussian.py to create tiny fixtures"
