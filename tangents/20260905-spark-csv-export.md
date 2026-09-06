---
id: 20260905-spark-csv-export
status: assess
priority: high
budget_cycles: 4
escalate_if: any zero-turn/permission launch fail (stop environmental immediately); or 2 live Stage 3 cycles still ending all_download_strategies_failed after one focused export patch
origin: project-ledger proposed step (appraisal-pipeline:spark-csv); rescope after harness-only cycles 1-2 (2026-09-05)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Fix/verify NTREIS Spark CSV export (all_download_strategies_failed)

## Why
Stage 3 comps must land a Spark CSV so Stage 4 / MLS import can attach comps. Core ledger blocker `appraisal-pipeline:spark-csv` still gates "fully processed" orders when search succeeds but export captures nothing. Revenue path: tax → diagnostics → **comps CSV** → report. Prior 2026-09-05 execute attempts never ran Stage 3 (permission/harness failures only); the CSV-less orders remain on disk, so the product goal is unchanged and now gets its first real live attempt on post-`35ac67d` export code.

## Done when
- [ ] **Launch gate evidence** exists for this execute cycle: the executor session actually takes ≥1 tool turn and leaves a run receipt under `C:\Users\lkmot\factory-context\code\fleet-triage\coo\live\` or `coo\tmp\` for this id. If the launch instead hits the zero-turn permission gate ("insufficient permission to proceed. Re-run with --auto medium or --auto high"), record Outcome `failed (environmental: yes)` with the live log path and make **no further product attempts** this cycle — the harness, not this contract, is broken.
- [ ] A live Stage 3 run **during this tangent** writes `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline\workfiles\by_address\<slug>\comps\spark_export.csv` with ≥1 data row (not header-only). Primary slug `1804_caladium_dr_corinth_tx_76210`; fallbacks `1208_perdenalas_trl_westlake_tx_76262`, `1441_companero_st_haslet_tx_76052`. CSV mtime must be newer than this cycle's `run_started`.
- [ ] Same run leaves corroborating comps artifacts in that order's `comps/` (e.g. refreshed `matrix_search_results.jpg` and/or `matrix_export_page.jpg`, or export success metadata/log) and the export path does NOT end with `reason=all_download_strategies_failed` (check run JSON `result.message` and the run's spark payload).
- [ ] MLS no-CSV skip is cleared for that order via **disk/discovery only** (no SFREP COM): prove `comps/spark_export.csv` is resolvable the way Stage 4 would resolve it (grep/call the discovery path in `agent/truetracts_context.py` and/or `agent/pipeline.py`, or a small Python one-liner importing that resolver and printing the found path). If `truetracts_mls_import_status.json` already exists for that order, it must not record a missing-CSV skip. Do NOT create a full Stage 4 run solely to prove this.
- [ ] Write-back recorded: outcome on `C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260905-spark-csv-export.md` (Outcome section, plus `tangents.json` completed entry per loop convention) and `C:\Users\lkmot\.factory\knowledge\project-ledger.json` step `appraisal-pipeline:spark-csv` flipped with outcome text + **absolute** artifact paths. Clear blocker `spark-csv` only if the live CSV success above is proven.

## Out of scope
- **COO harness repair** (`coo-loop-v3.sh`/`v4.sh` bash syntax, `flock`, live loop PIDs, patch re-apply). If the execute launch cannot get past the permission gate, stop with environmental failure and recommend a separate harness tangent — do not debug bash inside this tangent.
- fm23 radius/type controls (`20260905-ntreis-fm23` / `appraisal-pipeline:ntreis-fm23`). If mandatory-coverage blocks before export, capture the artifact and stop.
- Auth/session rearchitecture; Clareity redesign; portal mass actions; storage-state rebuild campaigns (existing `ntreis_matrix` state path is what it is — if stale, that is an environmental fail or a one clean re-auth via the existing portal_auth path only).
- Full Stage 4 TrueTracts workflow, SFREP COM sessions, report completion.
- Unrelated Stage 3 failure modes (filter-population blanks, CSV fieldname explosion, 100-row price-band merge, `format_readback_mismatch` as primary reason) — label and recommend a separate tangent only.
- Polar/other download rescuers outside Matrix Spark `_download_export_format`.
- Mass email, production deploy, DNS/network changes, data deletion; cleaning/reverting unrelated dirty files in the pipeline working tree.

## Context (verified during rescope, 2026-09-06)
- **Ledger** `C:\Users\lkmot\.factory\knowledge\project-ledger.json`: project `appraisal-pipeline` (core); blockers `ntreis-fm23` + `spark-csv` (since 2026-08-06); next step `appraisal-pipeline:spark-csv` still `status: proposed`, `outcome: null`, `dispatched_at: null`. `C:\Users\lkmot\.factory\knowledge\ledger-outcomes.jsonl` oscillates (evidence-clear 09-03/09-04, still-live 09-05 with `comps_partial_csv: true`).
- **Precedent PARTIALs** in `C:\Users\lkmot\.factory\knowledge\tangents.json` completed list: Caladium `20260806T090200-...-comps`, Perdenalas `20260807T210600-...-comps`, Companero `20260811T210500-...-comps` — search OK, then `all_download_strategies_failed`; Heidi `1325_heidi_dr_plano_tx_75025` Stage 4 "MLS import skipped (no CSV)".
- **2026-09-05 harness precedent for this id**: cycles 1-2 were launch-only failures — run 1 non-start 21:52; run 2 `num_turns: 0` "insufficient permission to proceed" after 187.9s, session `02442482-32c9-4f30-80b8-fa6c35634ad3`, live log `coo/live/20260905-spark-csv-export.execute.live.log`; cycle 3 never launched (assessor failed twice). Root cause shared with `20260905-ntreis-fm23`: execute launched without `--auto`. The `--auto` injection now exists in coo-loop-v4.sh (L141 `EXEC_AUTO=${COO_EXECUTE_AUTO:-medium}`, L145/147 launch lines), but live loop instances may still be running pre-fix code — hence the launch gate above. Full pre-rescope evidence is archived in git history of this file (feature/coo-loop branch).
- **Disk targets still CSV-less** (verified): each of the three slugs has only `comps\matrix_search_results.jpg` + `comps\matrix_spark_error.jpg` (Aug 6/7/11) plus subject/tax artifacts; no `spark_export.csv`, no `truetracts_mls_import_status.json`. Fleet-wide: 16 `spark_export.csv` successes elsewhere (post-08-26), 18 `matrix_spark_error.jpg` (mixed causes — not all are download failures).
- **Code hot path**: `agent\stages\stage3_matrix_spark.py` — `_download_export_format` at L2139 (opens Export.aspx, records "Export N Records", selects format via `SPARK_EXPORT_FORMAT`/`SPARK_EXPORT_OCCURRENCE`, readback check); Strategy 1 `expect_download` timeout=15000 at L2211; Strategy 2 click + body capture; Strategy 3 `__doPostBack`/JS click + poll; `payload["reason"] = "all_download_strategies_failed"` at exactly L2301. Success path writes `comps/spark_export.csv` (~L3434). Commit lineage includes `35ac67d` (resilient export helpers) plus later hardening (`041ee19` CSV quality validation, `4b8cc8f` SUCCESS return fix, `8c1ae3e` mandatory-field gate, `838ef9f` archive copy).
- **Entry points**: `python tools/run_stage3_single_case.py --subject-file <json> --workfile-root workfiles` (prints one JSON body: address, workfile_dir, status, message, elapsed_seconds, files); alternative env-var wrapper `tools/_autonudge_run_stage.py` with `AUTONUDGE_STAGE=3` + `AUTONUDGE_ADDRESS/CITY/STATE/ZIP/COUNTY` + `WORKFILE_DIR`. Subject JSON pattern: `tools/_tmp_subject_denham.json` / `tools/_tmp_subject_pine_meadow.json` (SubjectProperty fields; file loader tolerates utf-8-sig/utf-16).
- **Auth**: storage state `C:\Users\lkmot\.motto-appraisal-pipeline\browser-state\ntreis_matrix.json` (+ `ntreis_matrix_chrome_profile`); credentials via Doppler project `auth-userpass` config `prd` (NTREIS user/pass; wrapper convention `/ auth-userpass-prd` used by all prior stage runs). KB: Stagehand + Playwright on Legion; NTREIS is a known flaky surface (kb error pattern `ntreis`, 11 sessions).
- **MLS consume path**: `agent\truetracts_context.py` and `agent\pipeline.py` discover `comps/spark_export.csv`; Stage 4 writes `truetracts_mls_import_status.json`.
- **Full prior grounding + flow diagram**: `C:\Users\lkmot\.factory\specs\2026-09-06-contract-fix-verify-ntreis-spark-csv-export-all_download_strategies_failed.md` and rescope spec `C:\Users\lkmot\.factory\specs\2026-09-06-spark-csv-export-rescope.md`.
- **Repo note**: `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline` working tree is dirty — do not revert or clean; run from current tree state.
- **Sister fence**: `tangents/20260905-ntreis-fm23.md` (parked) owns radius/type controls; this id owns CSV capture only.

## Approach sketch
1. **Launch gate (mandatory first)**: confirm this session can act (≥1 real tool turn), then immediately append `run_started` + a short preflight note to this file. If the environment is permission-blocked/zero-turn, Outcome = `failed (environmental: yes)` citing the live log; stop.
2. **Preflight**: confirm `_download_export_format` present in `agent/stages/stage3_matrix_spark.py`; check `ntreis_matrix` storage state file exists/age; build `tools/_tmp_subject_caladium.json` mirroring the Denham pattern for `1804 Caladium Dr, Corinth, TX 76210` (county Denton).
3. **One live Stage 3 run** from the pipeline repo with the same auth wrapper convention as prior successful comps pulls (Doppler `auth-userpass/prd`): `python tools/run_stage3_single_case.py --subject-file tools/_tmp_subject_caladium.json --workfile-root workfiles`. Capture the stdout JSON into the Outcome block / `coo/tmp/`.
4. **Success path**: `comps/spark_export.csv` exists with ≥1 data row past header and sensible size; corroborating screenshot/metadata refreshed this run; run a discovery one-liner proving `truetracts_context`/`pipeline` resolution finds the CSV; write back ledger + `tangents.json` + this file's Outcome; done.
5. **Failure = `all_download_strategies_failed` only**: inspect same-run `matrix_spark_error.jpg` + logs; harden `_download_export_format` **once** (e.g. longer expect_download timeout, response listener for the Export.aspx CSV body, avoid double-click racing strategies 1→2, careful reuse of the longer `download_file` pattern); re-run the same order or the next fallback once.
6. **Any other fail reason** (fm23 mandatory fields, format_readback_mismatch, filter populate, auth): PARTIAL with artifacts + a recommended new tangent id; do not burn remaining budget on filters/auth.
7. **Escalate** without further silent reloops if: zero-turn launch recurs, or two live cycles still end `all_download_strategies_failed` after the one focused patch.


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
run_started: 2026-09-05T23:17:27-05:00
