# rql-repro — companion reproducibility package for RQL

**Date:** 2026-09-17 (Europe/Dublin)  
**Purpose:** Runnable offline RQL compile stack, dataset **registry** (no multi-GB binaries in git), synthetic fixtures, and small result smoke fixtures.

**Research / narrative repo (thesis, journal, OKF):**  
https://github.com/vijaykumarjob0701/rql-rag-query-language

**This companion:**  
https://github.com/vijaykumarjob0701/rql-repro

See [`EVIDENCE.md`](EVIDENCE.md) for the split checklist.

## What this is / is not

| Is | Is not |
|----|--------|
| Offline parse → plan → emit (toy E2E) | Live vector-DB execution |
| Synthetic Gaussian fixtures + download **instructions** | SIFT1M / BEIR binaries in git |
| Pinned deps + pytest smoke | Citation-ready P0 FANNS / RAG judgments |

## Quick start

```bash
cd rql-repro
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Unit / offline smokes
python -m pytest code/tests -q

# E2E pipeline (offline; notExecuted)
python code/rql_pipeline.py --inputs code/examples/toy --validate --run-id smoke

# Regenerate tiny synthetic fixtures
python datasets/synthetic/generate_gaussian.py --n 128 --d 8 --seed 42 \
  --out datasets/synthetic/fixtures/tiny
```

## Layout

```
datasets/     REGISTRY.md, synthetic fixtures, download instructions
code/         rql_parser / rql_planner / rql_adapters / rql_pipeline + schemas + tests
colab/        FANNS notebook + LINKS.md (Drive URL)
results/      drop metrics here; fixtures/ holds small committed smoke evidence
```

## Cite

See [`CITATION.cff`](CITATION.cff) and [`cite.md`](cite.md).

## License

MIT — see [`LICENSE`](LICENSE).
