---
id: 20260906-e2e-stage4-truetracts-repair
status: assess
priority: high
budget_cycles: 6
escalate_if: 2 failed live Stage-4 execute cycles after preflight (auth valid + subject JSON ready), OR google_secure_browser_block persists after one bounded reseed-refresh attempt, OR create-modal address bind fails the same way twice (address_not_committed) with no new selector evidence
origin: pinned-session:c8b23b5d-e1be-452c-b9b4-3eb073b825e6
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# e2e Stage 4: TrueTracts repair after site remodel

## Why
Stage 4 is the next core revenue domino after Stage 3. TrueTracts remodeled its UI (operator pin 2026-08-31); Stage 3 is now in its best state (`appraisal-pipeline:ntreis-fm23` closed 2026-09-06 on 308 Big Sky). Post-remodel code already landed (08-31 → 09-05) and one same-day autonudge SUCCESS exists on Big Sky, but the COO-facing work is incomplete until (a) a contract-gated daemon/run path is proven on a Stage-3-ready order with non-empty Stage-4 artifacts, (b) the e2e UI chain doc reflects the *current* post-Saguaro flow (findings still contain stale OPEN notes), and (c) Stage 3 → Stage 4 handoff is artifact-verified (`spark_export.csv` discovered + MLS status/handoff fields).

## Done when
- [ ] **Live Stage-4 acquisition pass (no manual UI babysitting during the run)** on one Stage-3-ready guinea-pig order, producing runner stdout JSON (`status: success`) saved to `coo/outcomes/20260906-e2e-stage4-truetracts-repair-run.json` or order `metadata\stage4_*.json`, plus under the order's `subject\`: `truetracts_workflow_status.json` with all five workflow steps navigated/settled, at least one heavy export artifact (`Report.tdcx` or `workfiles.zip`, non-zero), and `truetracts_export_harvest.json` and/or `truetracts_export_verification.json` (fatal `export_subject_mismatch` = FAIL; `tdcx_subject_block_absent` tolerated). Primary guinea pigs (TT-absent + tax + CSV): `2000_brazos_ct_westlake_tx_76262` → `1433_thistlewood_ln_grapevine_tx_76051` → `15060_cactus_blossom_blvd_fort_worth_tx_76052`; reuse-path fallback only after one diagnostic capture; never re-run Big Sky for a second SUCCESS; never use 11452 Snyder (ban precedent).
- [ ] **Stage 3 → Stage 4 handoff non-empty proof** on the same order: `comps\spark_export.csv` ≥1 data row AND `subject\truetracts_mls_import_status.json` (or equivalent) shows discovery with non-empty `csv_path` under that order's `comps\` (Big Sky shape). MLS in-UI attach staying `opened:false` is acceptable if discovery+CSV path is correct and Stage 4 otherwise succeeded.
- [ ] **e2e chain document updated** at `tools\_exploration\e2e_stage4_ui_chain.md` (dated 2026-09-06+): entry URLs, `truetracts_portal` storage key, create-modal phases (Subject Property Info → Detached → features/`#gla`/`#stories` → 2055/Q4/C3 → Create Session), Google Places bind rule, Update Heatmap/`ss_not_defined` honesty, five workflow steps, export + subject-verification/ban list, harvest note, failure codes, runner entrypoints. Plus a 2026-09-06 header in `truetracts_findings.md` superseding stale OPEN sections (Saguaro/Glenhaven/Big Sky resolutions).
- [ ] **Write-back**: tangent Outcome section; `tangents.json` completed row for the slug with artifact paths; ledger `appraisal-pipeline:truetracts-reseed` → verified/done with evidence if login was healthy (or operator reseeded mid-cycle); if auth-blocked, leave flagged and escalate.

## Out of scope
- Stage 3 comp-selection logic (sibling `20260906-e2e-stage3-comp-certainty`); Stage 5 SFREP assembly/delivery (sibling `20260906-e2e-stage5-sfrep-wiring`)
- TrueTracts account changes, purchases, plan upgrades, credential rotation (hard fence)
- Google re-login beyond ONE bounded attempt via existing `refresh_truetracts_state_from_persistent_profile.py`; still blocked → stop with the exact reseed command
- REST `/session/with-subject` API rewrite (pb-0064) — recommend-only
- NTREIS fm23 / spark-csv redesign (fm23 verified; spark-csv stays on `20260905-spark-csv-export`)
- Mass email, production deploys, DNS/network changes, data deletion (hard fences); multi-order campaigns (one guinea pig + one fallback max)

## Context (verified during scoping)
- Repo `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline`; `agent\stages\stage4_truetracts.py` (`run()` ~L4982, `_type_address_and_pick_suggestion` ~L1191, `_wait_for_address_bind_evidence` ~L1557, `_commit_pending_heatmap` ~L3032, `_verify_export_artifacts_subject` ~L311, `#stories` ~L1821); runners `tools\_autonudge_stage4.py <subject.json> <workfile_root>` and `tools\run_stage4_single_case.py --subject-json … --workfile-root …`; subject JSON shape per `tools\_tmp_subject_denham.json`; defaults form 2055 / Q4 / C3; entry URL `https://truetracts.truefootage.tech`.
- What is different this time: prior failure classes all have landed fixes (google_secure_browser_block → reseed path; modal timeout → cleared Glenhaven; shells/Places-bind → fixed live Saguaro 09-05; ss_not_defined → Update Heatmap commit; export_subject_mismatch → ban list + verification). Decisions 08-31/09-01/09-04/09-05 lock the flow. This tangent = COO-scorable proof + chain doc + handoff gate + write-back, not UI rediscovery.
- Disk-verified Stage-3-ready orders: Brazos/Thistlewood/Cactus (tax + CSV + zero TT); Big Sky full TT suite incl. `truetracts_mls_import_status.json` `handoff.ready:true` + `csv_path` → `comps\spark_export.csv`. Storage `workfiles\browser_state\truetracts_portal.json` (mtime 08-10 on disk; Big Sky refreshed to 14 cookies / 31.7h age at runtime). Doppler `auth-userpass-prd` pattern; memory gate ≥8 GB free (Big Sky: 12.1 GB).
- Precedent: `20260905-glenhaven-harvest-verify` (SUCCESS; TT re-run fenced there), `20260905-spark-csv-export` (stage4 consume path), `20260905-ntreis-fm23` (Stage 3 SUCCESS; harness `--auto` requirement). issue_funnel's "abandon TT for API" recommendation is NOT adopted here. Full lineage in `tangents/20260906-e2e-stage4-truetracts-repair.md` + spec copy `C:\Users\lkmot\.factory\specs\2026-09-06-contract-10.md`.

## Approach sketch
1. Preflight (no portal): RAM ≥8 GB; storage-state cookie check; build `tools\_tmp_subject_brazos.json`; confirm CSV present / TT absent.
2. Skim stage4 helpers + Big Sky success-shape JSONs as templates (no Stage 3 edits).
3. One live run: `python tools/_autonudge_stage4.py tools\_tmp_subject_brazos.json workfiles` (Doppler auth-userpass-prd); capture stdout to `coo/outcomes/20260906-e2e-stage4-truetracts-repair-run.json`.
4. Verify artifacts; on `address_not_committed`/`ss_not_defined` one diagnostic capture + one bounded fix (second identical failure → escalate); on `google_secure_browser_block` one reseed refresh then stop if blocked.
5. Author `e2e_stage4_ui_chain.md`; supersede stale OPEN sections in findings.md.
6. Write back tangent Outcome, tangents.json row, ledger reseed verify; recommend-only notes for MLS attach polish, Stage 5, API path, residual spark-csv orders.


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
run_started: 2026-09-06T14:26:08-05:00
