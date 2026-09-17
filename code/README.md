# RQL offline compile stack (companion copy)

**Date:** 2026-09-17 (Europe/Dublin)  
**Source:** copied from research repo `experiments/harness/` (+ `schemas/`, `examples/toy/`).  
**Policy:** offline / deterministic; never opens sockets or hits live vector DBs.

## Packages

| Package | Role |
|---------|------|
| `rql_parser/` | Toy `.rql` → LogicalPlan |
| `rql_planner/` | LogicalPlan → PhysicalPlan (capability profiles) |
| `rql_adapters/` | PhysicalPlan → vendor emit sketches (JSON/SQL) |
| `rql_pipeline.py` | E2E CLI glue |
| `schemas/` | Logical/Physical JSON Schema + examples |
| `examples/toy/` | Four toy `.rql` files |
| `tests/` | Offline unit / validate scripts + pytest wrappers |

## Run

From companion repo root (with `pip install -r requirements.txt`):

```bash
python code/rql_pipeline.py --inputs code/examples/toy --validate --run-id smoke
python code/tests/test_rql_parser.py
python code/tests/test_rrf_fusion.py
python -m pytest code/tests -q
```

Canonical narrative and journals remain in the research repo.
