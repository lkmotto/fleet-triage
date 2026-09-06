---
id: 20260906-e2e-stage4-truetracts-repair
status: approved
priority: high
budget_cycles: 6
escalate_if: 2 failed live Stage-4 execute cycles after preflight (auth valid + subject JSON ready + CSV gate green), OR google_secure_browser_block after one bounded reseed-refresh, OR address_not_committed twice with no new selector evidence, OR ss_not_defined twice after one bounded recovery fix, OR MLS attach still file_attached:false after one diagnostic + one bounded selector fix
origin: pinned-session:c8b23b5d-e1be-452c-b9b4-3eb073b825e6; rescope-after-assessor:38fe54ae-600f-4ffe-beef-a24312a796e0; operator-addendum-20260906-1505-comp-carry
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# e2e Stage 4: TrueTracts repair after site remodel (comp-carry re-scope)

## Why
Stage 4 is the core revenue step after Stage 3. Cycle 1 proved session create + workflow navigation on Brazos but failed export (`ss_not_defined`) and never attached Stage-3 comps; operator review found improper TDCX addresses whenever `spark_export.csv` was missing or unused (TrueTracts auto-picks comps). Closing requires a CSV-gated, MLS-attached, provenance-checked live export on a geo-clean guinea pig, plus chain docs and write-backs — not another discovery-only run.

## Done when
- [ ] **Live Stage-4 SUCCESS** on primary `1804_caladium_dr_corinth_tx_76210` (one local-geo fallback only if Caladium bails with artifacts): runner JSON `status: success` at `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage4-truetracts-repair-run.json`; order `subject/truetracts_workflow_status.json` (5 steps navigated/settled); non-zero `Report.tdcx` and/or `workfiles.zip`; `truetracts_export_harvest.json` and/or `truetracts_export_verification.json`; fatal on `export_subject_mismatch` (`tdcx_subject_block_absent` tolerated); never Big Sky second SUCCESS; never 11452 Snyder.
- [ ] **COMP-CARRY proof** on the same order: `comps/spark_export.csv` ≥1 data row; `subject/truetracts_mls_import_status.json` with non-empty order-local `csv_path` AND `file_attached: true` (plus non-empty `selected_comp_ids` where UI allows, from CSV `MLS#` / `selected_comps.json`); plus comp-address diff artifact at `coo/outcomes/20260906-e2e-stage4-truetracts-repair-comp-diff.json` (or order `subject/`) with `match_rate` + unmatched lists vs the `spark_export.csv` set. Discovery-only (`opened:false`, `file_attached:false`) does NOT satisfy. Attach technically blocked after one diag + one bounded fix → PARTIAL + rescope note, not SUCCESS.
- [ ] **Docs**: `tools/_exploration/e2e_stage4_ui_chain.md` dated 2026-09-06+ (entry URLs, storage keys, create-modal phases, Google Places bind rule, MLS import open/attach selectors as found, Update Heatmap/`ss_not_defined` honesty + recovery limits, five workflow steps, export + subject-verification/ban list, harvest note, failure codes, runners, comp-carry gate, contaminated-order list); 2026-09-06+ header on `truetracts_findings.md` superseding stale OPEN sections and recording the Brazos recurrence + this cycle's result.
- [ ] **Write-back**: mandatory `## Outcome` on `tangents/20260906-e2e-stage4-truetracts-repair.md` (missing Outcome = incomplete cycle); `tangents.json` completed row with absolute artifact paths; ledger `appraisal-pipeline:truetracts-reseed` verified if login healthy else flagged + escalated with exact reseed command; contaminated artifact paths listed; no artifact deletes (operator-approved cleanup only).

## Out of scope
- Stage 3 CSV geo/quality redesign and new Matrix pulls (`20260905-spark-csv-export`); Stage 3 comp-certainty sibling; Stage 5 SFREP sibling
- TrueTracts account changes, purchases, plan upgrades, credential rotation (hard fence)
- Google re-login beyond ONE bounded attempt via existing `tools/refresh_truetracts_state_from_persistent_profile.py`; still blocked → stop with the exact reseed command
- REST `/session/with-subject` rewrite (pb-0064) — recommend-only; multi-order campaigns; Big Sky re-run; Snyder reuse
- Mass email, production deploys, DNS/network changes, data deletion (hard fences); SFREP COM sessions (not authorized); killing arbitrary user apps to free RAM (environmental stop instead)

## Context (verified during scoping)
- Repos: pipeline `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline`; COO `C:\Users\lkmot\factory-context\code\fleet-triage`.
- Cycle-1 fail: `coo/tmp/stage4_brazos_run.log` + `workfiles/by_address/2000_brazos_ct_westlake_tx_76262/subject/truetracts_failure_metadata_20260906_194816.json` — `ss_not_defined` after heatmap commit + Qwen OK + 5 steps True; MLS `ready:true`, `opened:false`, `file_attached:false`, `selected_comp_count:0`; no heavy export. Assessor RESCOPE (not environmental).
- Auth healthy: "Reused persisted TrueTracts session (login skipped)"; storage persisted to `C:\Users\lkmot\.motto-appraisal-pipeline\browser-state\truetracts_portal.json` (14:48 today); repo copy `workfiles\browser_state\` stale 08-10.
- CSV geo (checked 2026-09-06): Brazos/Thistlewood/Cactus/Glenhaven polluted (Houston-area). Caladium = 100 local rows (60 Corinth/40 Denton, zip 76210), mtime 15:01, `MLS#` populated, `realist_tax.pdf` present, zero TT artifacts, subject JSON `tools/_tmp_subject_caladium.json`. Big Sky local but contaminated + re-run banned. Lark/Sundown/Parkmont have local CSVs but already carry TDCX (reuse-path diagnostic only).
- Contaminated for stage-4 evidence (list, do not delete): 771 Monticello, 4424 Santa Fe, 3808 Denham, 6804 Richfield, 308 Big Sky.
- Code: `agent/stages/stage4_truetracts.py` — `_apply_mls_import` ~L3289, `_resolve_mls_import_handoff` ~L3199, `_prime_selected_comp_ids` ~L3229, `_commit_pending_heatmap` ~L3032, SS gate ~L6546-6576, MLS status write ~L6102, optional `TRUETRACTS_REQUIRE_MLS_IMPORT` ~L6122; `agent/truetracts_context.py` builds `selected_comp_ids` from `selected_comps.json`/CSV `MLS#`. Runners `tools/_autonudge_stage4.py` / `tools/run_stage4_single_case.py`; Doppler `auth-userpass`/`prd`; RAM gate ≥8 GB (scope-time free ~3.4 GB — must clear).
- What is different this time: geo-clean CSV-gated primary; comp-carry as hard done-when with diff artifact; `ss_not_defined` treated as open recurrence with bounded recovery then escalate; executor exit protocol (Outcome + named outcomes path) contract-mandatory after cycle-1 skipped both.

## Approach sketch
1. Append `run_started` + preflight note to the tangent BEFORE portal work; tee run log to the named outcomes path from the start.
2. Preflight (no portal): RAM ≥8 GB; storage-state check; Caladium CSV row count + local-geo spot check; tax present; resolve `selected_comp_ids` (established `truetracts_context` path or minimal `selected_comps.json` input; if unresolvable, record and attempt full-CSV attach).
3. Skim only: `_apply_mls_import`, `_commit_pending_heatmap`, SS recovery; Big Sky MLS JSON as anti-template.
4. One live run: `doppler run --project auth-userpass --config prd -- python tools/_autonudge_stage4.py tools/_tmp_subject_caladium.json workfiles`; stdout to `coo/outcomes/20260906-e2e-stage4-truetracts-repair-run.json`.
5. On `ss_not_defined`: one diagnostic package + one bounded recovery fix + one re-run; second identical fail → escalate.
6. On MLS not attached: one selector diagnostic + one bounded `_apply_mls_import` fix; still blocked → PARTIAL + rescope note (no fake SUCCESS).
7. On SUCCESS: comp-diff JSON, subject verification check, `e2e_stage4_ui_chain.md` + findings header, Outcome + tangents.json + ledger write-backs, governance record.
8. On auth block: one bounded reseed via existing refresh script; still blocked → stop with exact command in Outcome.


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
