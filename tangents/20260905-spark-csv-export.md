---
id: 20260905-spark-csv-export
status: rescope
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

## Assessor verdict
=== VERDICT: RELOOP === First failure, contract verified sound, 0/4 cycles consumed — executor non-start produced no artifacts (Caladium comps/ still 08-06-only, no CSV, no MLS status, no write-back); relaunch with mandate to leave run artifacts as evidence.
run_started: 2026-09-05T22:11:56-05:00

## Assessor evidence (cycle 2 of 4)
- Run 2 verified directly: NO Outcome block appended for run 2; `coo/live/20260905-spark-csv-export.execute.live.log` is a 470-byte failure JSON: `num_turns: 0`, "Exec ended early: insufficient permission to proceed. Re-run with --auto medium or --auto high", session `02442482-32c9-4f30-80b8-fa6c35634ad3`, 187.9s. The executor took zero turns — not a plan or artifact failure.
- Done-when re-verified 0/4: Caladium `comps/` holds only `matrix_search_results.jpg` + `matrix_spark_error.jpg` (both 8/6 04:10); no `spark_export.csv` for Caladium, Perdenalas (8/7 artifacts), or Companero (8/11 artifacts); no `truetracts_mls_import_status.json` anywhere under the Caladium order; ledger step `appraisal-pipeline:spark-csv` still `status: proposed`, `outcome: null`, `dispatched_at: null`; no `tangents.json` entry; no Caladium subject JSON built. Zero pipeline-repo or workfile files modified since 22:00 that trace to this tangent.
- Root cause shared with 20260905-ntreis-fm23 (sessions 5634a6ec / 514c7e4b): execute launched without `--auto` → deterministic `num_turns:0` permission gate. The fix (coo/tmp/patch_coo_loop_20260906.py → coo-loop-v3.sh/v4.sh: `EXEC_AUTO=${COO_EXECUTE_AUTO:-medium}` injected into both launch branches; session_id capture fixed) landed 22:17:38 — AFTER run 2 died at 22:15:49, so run 2 never benefited.
- CAUTION: post-patch dispatch still failed (strategic-outcomes-verify ~22:30, `num_turns: 0`, session `dac3138a-064b-4443-97f3-adbe0ee1555a`), and coo-loop.log shows `coo-loop-v4.sh` bash syntax errors (line 255) + `flock: command not found` (line 26) after 22:17. The patch was applied in-place while loop instances were live — live loop processes are likely still executing pre-fix or byte-offset-corrupted code.
- Budget: 2 of 4 cycles consumed (run 1 non-start 21:52, run 2 permission gate 22:11). **escalate_if "2 failed cycles": MET.** RELOOP barred (second failure of contract). Scope adherence: clean by vacuity — executor made no changes at all.
- Recommendation (Scoper + lkmot): the contract itself is sound — all pointers re-resolved during this assessment (spec file exists; `tools/run_stage3_single_case.py`, `tools/_autonudge_run_stage.py`, all three workfile dirs, ledger keys verified). Do NOT rewrite the goal. Park until the COO loop is cleanly restarted (kill live v3/v4 instances, relaunch ONE instance of the patched script, confirm `--auto medium` in the execute launch), then dispatch the fresh contract. If cycle 3 fails for ANY reason, park and escalate to lkmot — no further reloop/rescope on this tangent.

## Assessor evidence (cycle 3 assessment, 2026-09-05 ~22:55)
- No cycle 3 execution occurred. Tangent file unchanged between 22:11 dispatch and this assessment (no new Outcome block, no third `run_started`); `coo/live/20260905-spark-csv-export.execute.live.log` still holds the run-2 failure JSON (470 B, `num_turns: 0`, permission gate, session `02442482-32c9-4f30-80b8-fa6c35634ad3`, 187.9 s), last write 22:15:49.
- Root cause of the empty cycle 3: the loop's own assessor phase failed twice for this tangent — `ASSESSOR FAILED 20260905-spark-csv-export (retry next sweep)` at 22:39:28 and 22:49:22 in `coo/coo-loop.log` — so the executor was never re-launched. The broken harness, not the contract, is consuming cycles.
- Harness still broken mid-flight: `flock: command not found` (v4.sh line 26) fired again at 22:49:22, and `gitlock timeout` warnings follow both assessor failures. Live bash processes started 21:45:34 (matching v4 launch + `coo/.git.lock` creation) are still running the pre-fix/broken script. coo-loop-v4.sh remains 272 lines (2 more than the 22:17:38 pre-patch size) — the in-place patch while live is confirmed corrupt.
- Done-when re-verified 0/4 by direct inspection at ~22:55: Caladium `comps/` still only `matrix_search_results.jpg` + `matrix_spark_error.jpg` (8/6 04:10); no `spark_export.csv` for Caladium/Perdenalas/Companero; no `truetracts_mls_import_status.json` under any of the three; ledger step `appraisal-pipeline:spark-csv` still `status: proposed`, `outcome: null`, `dispatched_at: null`; no `spark-csv` entry in `C:\Users\lkmot\.factory\knowledge\tangents.json`.
- Contract pointers ALL resolve on re-check (cycle-2 note's unresolved pointer was a false alarm): `stage3_matrix_spark.py` lives at `agent\stages\stage3_matrix_spark.py` (3703 lines; Strategy 1 expect_download at exactly L2211, `payload["reason"] = "all_download_strategies_failed"` at exactly L2301 — scoping's line refs precise); `tangents.json` lives at `C:\Users\lkmot\.factory\knowledge\tangents.json`; spec file, `tools/run_stage3_single_case.py`, `tools/_autonudge_run_stage.py`, `agent/truetracts_context.py`, `agent/pipeline.py` all exist.
- Budget: 2 of 4 cycles consumed; **escalate_if "2 failed cycles" already MET as of cycle 2**. RELOOP barred (second contract failure). RESCOPE barred (no fresh contract may be produced while the Scoper/loop harness that would run it is itself failing — and the contract is verifiably sound).
- Scope adherence: clean by vacuity (executor made zero changes in both cycles).
- ESCALATE to operator (lkmot): park this tangent and repair the loop first. Concretely: (1) kill live bash instances from 21:18/21:45 running coo-loop v3/v4; (2) fix `flock` dependency on Git-Bash (line 26) and re-run `python coo/tmp/patch_coo_loop_20260906.py` against a CLEAN checkout of coo-loop-v4.sh (current file is 272 lines vs 270 pre-patch — the in-place patch half-applied); (3) bash -n the result; (4) relaunch ONE instance and confirm `--auto medium` lands in the execute launch line; (5) re-dispatch this unchanged contract. Do not rewrite the goal — it verified sound.

## Assessor verdict
=== VERDICT: RESCOPE === no verdict line
