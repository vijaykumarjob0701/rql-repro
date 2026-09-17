# Toy-parser–compatible RQL snippets

These files use the **tiny Hypothesis subset** implemented by
`experiments/harness/rql_parser/` (journal 0022). They are **not** the full
aspirational surface in `examples/*.rql` (EMBED / RERANK / WITH / …).

Canonical copies also live under `schemas/examples/*.rql`.

E2E offline (no live DB):

```bash
tooling/.venv/bin/python experiments/harness/rql_pipeline.py --inputs examples/toy --validate
```
