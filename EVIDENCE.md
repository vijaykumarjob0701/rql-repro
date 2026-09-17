# Evidence checklist — companion `rql-repro`

**Date:** 2026-09-17 (Europe/Dublin)  
**Paired research audit:** https://github.com/vijaykumarjob0701/rql-rag-query-language/blob/main/EVIDENCE.md

## What’s here vs research repo

| Item | Research repo | This companion |
|------|---------------|----------------|
| Thesis / journal / OKF narrative | **Yes** | Pointers only |
| Schemas + toy `.rql` | Canonical | **Copied** under `code/schemas`, `code/examples/toy` |
| Offline parser/planner/emit/E2E | `experiments/harness/` | **Runnable package** under `code/` |
| Unit / smoke result text | `experiments/results/...` | Small copies in `results/fixtures/` |
| Colab notebook + Drive link | `experiments/colab/` | **Copied** under `colab/` |
| Dataset binaries | Must not live in git | Must not live in git; registry + scripts here |
| P0 FANNS w/ GT | Missing | Registry + instructions; digests TBD after download |
| Live adapter / RAG judgments | Missing | Missing (same gaps) |
| Pinned `requirements.txt` | Missing at experiments root | **Present** (root) |

## Provided in this repo

- Runnable offline package + `requirements.txt` / `pyproject.toml`
- `datasets/REGISTRY.md` + `datasets/scripts/download_sift1m.md` (instructions only)
- `datasets/synthetic/` generator + tiny committed fixtures
- `results/fixtures/` smoke summaries (text/JSON only)
- `colab/` notebook + `LINKS.md`

## Still incomplete for venue-grade (same as research)

- P0 large-set FANNS with ground truth
- Filled SHA-256 digests for licensed downloads (fill after you download — do not invent)
- Live adapter smokes
- RAG judgments

## Recommendation (confirmed)

Keep narrative in the research repo; use this companion for **registry + code + small fixtures**.
