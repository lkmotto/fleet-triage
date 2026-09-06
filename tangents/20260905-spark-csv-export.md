---
id: 20260905-spark-csv-export
status: assess
priority: high
budget_cycles: 4
escalate_if: 2 failed cycles
origin: project-ledger proposed step (appraisal-pipeline:spark-csv)
scoped_by: coo-scoper
scoped_at: 2026-09-05
---
# Fix/verify NTREIS Spark CSV export (all_download_strategies_failed)

## Why
Stage 3 comps must land a Spark CSV so Stage 4 / MLS import can attach comps. Ledger blocker `appraisal-pipeline:spark-csv` (core `appraisal-pipeline`) still gates "fully processed" orders when search succeeds but export captures nothing. Revenue path: tax → diagnostics → **comps CSV** → report.

## Done when
- [ ] A live Stage 3 run during this tangent writes `workfiles/by_address/<slug>/comps/spark_export.csv` with ≥1 data row (not header-only) for a previously CSV-less order (primary `1804_caladium_dr_corinth_tx_76210`; fallbacks `1208_perdenalas_trl_westlake_tx_76262` or `1441_companero_st_haslet_tx_76052`).
- [ ] Same run leaves corroborating comps artifacts in that order's `comps/` (e.g. `matrix_search_results.jpg` and/or `matrix_export_page.jpg`, or export success metadata) and the export path does NOT end with `reason=all_download_strategies_failed`.
- [ ] MLS no-CSV skip is cleared for that order via checkable handoff/discovery: either `agent/truetracts_context.py` / `agent/pipeline.py` resolution finds `comps/spark_export.csv` as ready input, or an existing/new `truetracts_mls_import_status.json` no longer records skip for missing CSV. Do NOT open SFREP COM solely to prove this.
- [ ] Write-back recorded: outcome in `tangents/20260905-spark-csv-export.md` (Outcome section, plus `tangents.json` completed entry per loop convention) and `project-ledger.json` step `appraisal-pipeline:spark-csv` flipped with outcome text + absolute artifact paths.

## Out of scope
- fm23 radius/type controls (`20260905-ntreis-fm23`) — if mandatory-coverage blocks before export, capture artifact and stop.
- Auth/session rearchitecture; Clareity redesign; portal mass actions.
- Full Stage 4 TrueTracts workflow, SFREP COM sessions, report completion.
- Unrelated Stage 3 failure modes (filter population blanks, CSV fieldname explosion, 100-row price-band coverage) — label and recommend a separate tangent only.
- Mass email, production deploy, DNS/network changes, data deletion; cleaning/reverting unrelated dirty files in the pipeline working tree.
- Polar/other download rescuers outside Matrix Spark export.

## Context (verified during scoping)
- Ledger `C:\Users\lkmot\.factory\knowledge\project-ledger.json`: blocker `spark-csv` since 2026-08-06, step still `proposed`, 2026-09-05 evidence `comps_partial_csv: true`; `ledger-outcomes.jsonl` oscillates (evidence-clear 09-03, still-live 09-05).
- Precedent PARTIALs in `tangents.json`: Caladium 08-06, Perdenalas 08-07, Companero 08-11 (search OK, `all_download_strategies_failed`, no CSV); Heidi 08-02 Stage 4 "MLS import skipped (no CSV)".
- 14 orders CSV-less with spark error under `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\` (list in tangent file); 16 `spark_export.csv` successes on disk post-08-26.
- What is different this time: export plumbing landed (`35ac67d` resilient helpers; strategies at `stage3_matrix_spark.py` ~2211–2301) and fm23 path works; residual failures are a mix, so this is verify-then-patch-once, not a blind rewrite.
- Entry points: `tools/run_stage3_single_case.py --subject-file`; `tools/_autonudge_run_stage.py`; storage key `ntreis_matrix`; `auth-userpass/prd` wrapper convention; optional `SPARK_EXPORT_FORMAT`/`SPARK_EXPORT_OCCURRENCE`/`SPARK_PRICE_BAND`.
- MLS consume path: `agent/truetracts_context.py` + `agent/pipeline.py` discover `comps/spark_export.csv`; Stage 4 writes `truetracts_mls_import_status.json`.
- Full grounding + flow diagram: `C:\Users\lkmot\.factory\specs\2026-09-06-contract-fix-verify-ntreis-spark-csv-export-all_download_strategies_failed.md`; contract persisted at `C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260905-spark-csv-export.md`.

## Approach sketch
1. Pre-flight: confirm `_download_export_format` + Spark step present; check `ntreis_matrix` state age; build Caladium subject JSON (mirror `_tmp_subject_*.json` pattern).
2. One live Stage 3 run via `tools/run_stage3_single_case.py --subject-file` with workfile root = repo `workfiles/`.
3. CSV with ≥1 data row → validate structure, prove MLS discovery/handoff ready, write back; done.
4. Fail with `all_download_strategies_failed` only → harden capture ONCE (longer expect_download timeout, response listener for Export.aspx CSV body, avoid double-click racing strategies); re-run.
5. Any other fail reason → PARTIAL + recommend new tangent; do not burn budget on filters.
6. Two live cycles still failing post-patch → escalate per `escalate_if`.


## Executor instructions (pipeline section)

You are the Executor for this tangent. Rules:

1. Work ONLY toward the "Done when" items. The "Out of scope" fence is HARD — if the
   real path crosses it, STOP and write a rescope note instead of improvising.
2. If you discover the contract itself is wrong (goal unachievable as written, a
   context pointer doesn't resolve), do a MID-FLIGHT BAIL: stop, write the rescope
   note, exit. Do not wander.
3. Stay inside this repo's working area and the paths the contract names. SFREP COM
   sessions are forbidden unless the contract explicitly authorizes them.
4. Before exiting, append to THIS FILE (tangents/<id>.md):

## Outcome (filled by executor)
- status: success | partial | failed (environmental: yes/no)
- artifacts: <paths produced>
- what was done: <2-4 lines>
- what remains: <or "nothing — done-when fully met">
- rescope note: <only if bailing>
run_started: 2026-09-05T21:52:51-05:00
