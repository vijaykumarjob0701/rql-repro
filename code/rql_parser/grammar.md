# Toy RQL grammar (Hypothesis) — tiny subset

**Status:** Prototype frontend only. **Not** a full SQL engine. Maps to LogicalPlan `0.1.0-draft`.  
**Date:** 2026-09-16 (Europe/Dublin) · journal 0022

Full aspirational grammar lives in `docs/03-proposal.md`. This toy implements only what is needed to emit schema-valid trees for SEARCH / FILTER / FUSE.

## EBNF (implemented)

```ebnf
query          = retrieve_stmt ";" ? ;

retrieve_stmt  = "RETRIEVE" collection
                 search_clause
                 [ "WHERE" predicate ]
                 [ "ACL_HARD" ]
                 [ "FUSE" fuse_spec ]
                 [ "LIMIT" int ] ;

search_clause  = "SEARCH" search_arm ( "AND" search_arm )* ;

search_arm     = channel [ "ON" field ]
                 [ "METRIC" metric ]
                 ( "K" | "CANDIDATES" ) int
                 [ "QUERY" ( string | param ) ]
                 [ "VECTOR_REF" param ] ;

channel        = "DENSE" | "BM25" | "LATE" | "COLBERT" ;   (* COLBERT → Search_late *)

fuse_spec      = "RRF" [ "K" int ]
               | "LINEAR" "WEIGHTS" "(" number ( "," number )+ ")" ;

metric         = "cosine" | "l2" | "ip" | "dot" ;          (* dot → ip *)

collection     = ident ;
field          = ident ;
predicate      =  (* opaque text until ACL_HARD | FUSE | LIMIT | ; | EOF *)
string         = "'" [^']* "'" | '"' [^"]* '"' ;
param          = "$" ident ;
ident          = [A-Za-z_][A-Za-z0-9_]* ;
number         = digit+ ( "." digit+ )? ;
```

Comments: lines starting with `--` (after optional whitespace) are stripped before lexing.

## Semantic mapping → LogicalPlan

| Surface | IR |
|---------|-----|
| `SEARCH DENSE … K/CANDIDATES n` | `Search_dense` (`collection` from RETRIEVE; `metric` if given) |
| `SEARCH BM25 …` | `Search_bm25` |
| `SEARCH LATE` / `COLBERT` | `Search_late` (`channel: late`) |
| `WHERE pred` | `Filter` wrapping the search or fuse root; `predicate.expr` = opaque string |
| `ACL_HARD` | `predicate.aclHard: true` |
| `FUSE RRF [K n]` (≥2 arms) | `Fuse_rrf` (`k_rrf` default 60) |
| `FUSE LINEAR WEIGHTS (…)` | `Fuse_linear` (`alpha` array) |
| `LIMIT n` | If a search has no K/CANDIDATES, sets `k`; else recorded in `meta.notes` only (no Limit op in schema) |
| `QUERY '…'` / `$param` | `query.text` |
| `VECTOR_REF $x` | `query.vectorRef` |

## Explicitly out of scope (reject with ParseError)

`EMBED`, `WITH`/`CTE`, `RERANK`, `DIVERSIFY`, `EXPAND`, `REWRITE`, `TRAVERSE`, `VSIM JOIN`, `FILTER_MODE`, `OPTION`, `UNION`, `EXPLAIN`, sparse/DBSF/LTR/Condorcet fuse, nested subqueries.

## Honesty

Grammar and packaging are **Hypothesis**. Mechanisms named by ops (RRF, MaxSim, …) remain Established in literature; this parser does not re-prove them.


## Deferred: `REWRITE HYDE` (journal 0032)

HyDE mechanism is **Established** (Gao et al. ACL’23; OKF `knowledge/reads/hyde-2212.10496/`).  
Toy parser still **rejects** `REWRITE` / `WITH` CTE (out of scope above).  

**Suggested later EBNF (not implemented):**

```ebnf
(* aspirational — Hypothesis packaging only *)
with_cte     = "WITH" ident "AS" "(" rewrite_hyde ")" ;
rewrite_hyde = "REWRITE" "HYDE"
               "MODEL" string
               "TEXT" ( string | param )
               [ "INST" string ]
               [ "N" int ]
               "AS" ident ;
```

Maps toward LogicalPlan `Rewrite` / `Rewrite_hyde` feeding `Search_dense`. Do not implement until schema gains an explicit Rewrite op (or encode as annotated Search). Integrity: no IR metrics from supporting the parse.
