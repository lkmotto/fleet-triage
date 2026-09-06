---
id: 20260906-e2e-stage5-sfrep-wiring
status: running
priority: high
budget_cycles: 6
escalate_if: 2 failed live Stage-5 apply cycles after Phase A artifacts (diagnosis memo + payload-inventory.json) exist with the same root-cause class; OR free RAM cannot stay >= 8 GB around a single agent-owned SFREP session after one safe cleanup of agent-owned SfrepMcpServer processes only; OR Appraise-It/sfrep-mcp unavailable on Legion after one install/path check
origin: pinned-session:3c80cca2-de30-481c-8be7-de57ba1df66e
scoped_by: coo-scoper
scoped_at: 2026-09-06
rescope_of: cycles 1-2 environmental (1202s num_turns:0, 1/6 artifacts); assessor_session 0a6ed110-0c0a-43fa-837f-e502cc910c1f
---
# e2e Stage 5: SFREP report assembly wired to real workfile data (rescope)

## Why
Stage 5 (forms prefill / SFREP apply) is the last core domino for automated appraisal report production on core-tier project `appraisal-pipeline` (ledger goal: tax -> comps -> report without human back-office; current metrics flag `sfrep_failed: true`). Workfiles already carry tax/comps/context, but live SFREP reports stay placeholder-empty on the comp grid because of a selection-path miss plus a comp-grid apply gap. Closing workfile -> payload -> live-fill is directly revenue-critical.

This failed twice for environmental reasons (1202s `num_turns:0` watchdog kills with 0-byte exec logs), not contract reasons. What is different this time: (1) the diagnosis memo is complete and re-verified, so no diagnosis work remains; (2) the comp-source fix already sits uncommitted in the pipeline tree; (3) Phase A now always produces on-disk artifacts BEFORE any live/COM work, and Phase B is refused (not thrashed) while the RAM gate is red - so a watchdog kill can no longer zero a cycle.

## Done when
- [ ] **Diagnosis (credit + re-verify):** `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage5-sfrep-wiring-diagnosis.md` still exists stating (a) the Stage-5 field data source chain with file paths, (b) why placeholders appear (gate vs mapping vs apply vs session), (c) guinea-pig slug + evidence. If intact, leave as-is (append a one-line re-verification note at most). Do NOT rewrite.
- [ ] **Payload rebuild proof (Phase A, offline, no COM):** regenerating the Stage-5/forms bundle for guinea pig `6037_sundown_dr_fort_worth_tx_76114` with live apply off produces `<workfile>/sfrep/payload.json` with real subject identity (subject.address.street/city/state/zip = 6037 Sundown Dr / Fort Worth / TX / 76114) and a machine-readable inventory at `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-payload-inventory.json` containing at minimum: `key_count`, `empty_keys`, `comp_keys_present` (count + sample) or explicit note that comps are applied post-fill via the deep-fill path, `source_selection_path` used (must record the metadata artifact fallback), and unmapped/skipped categories.
- [ ] **Live apply proof (Phase B, opt-in, one session, RAM-gated):** only if free RAM >= 8 GB immediately before connect, with `SFREP_ALLOW_LIVE_APPLY=1` for this run only and `SFREP_APPLY_COMMAND` set: one guinea-pig apply via `tools/sfrep_apply.py --mode apply` targeted at one agent-owned Appraise-It PID (add `--process-id` CLI passthrough first), plus comp-grid fill for slots 1-3 via `agent/sfrep_deep_fill.py::fill_comp_grid` or equivalent `sfrep_field_set_text` (compType=SalesComparables, 1-based compIndex) since payload_fill cannot map comp keys; export `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-apply.json` (apply stdout/fill summary) plus refreshed `<workfile>/sfrep/report_full.pdf` or twin at `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-report_full.pdf`. If RAM stays red after one agent-MCP cleanup attempt: write `...-session-safety.md` with `status: deferred_ram_gate` + measured free GB, finish Phase A, mark Outcome partial (environmental: yes), and exit - no fake live attempts.
- [ ] **Zero-placeholder field checklist:** `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-field-checklist.md` (+ `.json` if scripted) listing required fields checked via MCP readback (`sfrep_field_get_text` / report status) after the real apply: subject identity + structure core (GLA/beds/baths/year built) + comps 1-3 sale price/address/GLA all non-blank and non-placeholder. "N/A - source absent in workfile" allowed only where the diagnosis proves the source artifact is missing (not a wiring miss).
- [ ] **SFREP session safety record:** `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-session-safety.md` logging free RAM before/after (>= 8 GB gate), single agent-owned session only (never PIDs 24604/39784/41636 or any user-owned instance), no delivery call, and session disposition per the 2026-09-04 decision (snapshot before close, zero standing sessions). Required after a live attempt OR an explicit RAM deferral.
- [ ] **Write-back:** Outcome section appended to `tangents/20260906-e2e-stage5-sfrep-wiring.md` with status, artifacts, and file paths changed (expect `agent/form_prefill_bridge.py`, `tools/sfrep_apply.py`, possibly a deep-fill hook); residual items recommend-only (delivery, Stage 3/4 siblings, C# canonical map, coo-loop 1202s runner hardening, Big Sky Stage 5 follow-on).

## Out of scope
- Stage 3 comp-certainty logic and Stage 4 TrueTracts repair/reseed (siblings `20260906-e2e-stage3-comp-certainty`, `20260906-e2e-stage4-truetracts-repair`)
- Any SFREP **delivery** to clients / TOTAL drop as a success criterion (`sfrep_report_deliver`, production client send) - hard fence, contract ends at recommendation
- Killing, closing, or writing into user-owned Appraise-It instances to free RAM (operator-owned; recommend only)
- Full C# `_canonicalMap` redesign in SfrepPayloadPlanner.cs (use the proven field_set_text/deep-fill path; recommend-only residual if ever still blocked)
- coo-loop runner changes (1202s zero-output crash class, `COO_STAGE_TIMEOUT=1200`) - recommend-only for a separate tangent
- Switching appraisal form software; new MCP image-set tooling beyond what the checklist requires (prefer document residual)
- Multi-order campaigns; second concurrent agent SFREP session; bulk live apply
- Mass email, production deploys, DNS/network changes, data deletion (hard fences)

## Context (verified during scoping)
- Machine: Legion. RAM free ~2.12 GB / 31.19 GB at scoping time (gate RED). User-owned `Sfrep.AppraiseIt` PIDs 24604 (9/6 9:56 AM), 39784 (9/4 7:27 PM), 41636 (9/6 2:37 PM); several short-lived `SfrepMcpServer` processes appear per session.
- Pipeline repo (active checkout): `C:\Users\lkmot\factory-context\code\github\lkmotto\motto-appraisal-pipeline`, branch `droid/appraisal-pipeline-v1-forms`. Do not use the stale `code-intel-stack\repos\...` clone. Tree is dirty: `agent/form_prefill_bridge.py` (+selection fallback to `metadata/artifact_selected_comps__*.json`, ~440 lines uncommitted) and `tools/sfrep_apply.py` (McpStdioClient accepts `process_id`, but the argparse CLI does NOT yet expose `--process-id`). Build on these; do not revert unrelated dirty files.
- Stage-5 chain: `agent/stages/stage5_export_deliver.py` -> `stage10_forms_prefill.py` (`_auto_apply_enabled()` requires `SFREP_ALLOW_LIVE_APPLY` in {1,true,yes,on} AND non-empty `SFREP_APPLY_COMMAND`; fail-closed by design) -> `form_prefill_bridge.generate_forms_prefill_bundle` -> optional `tools/sfrep_apply.py` -> sfrep-mcp `sfrep_payload_fill`.
- sfrep-mcp exe: `C:\Users\lkmot\sfrep-integration\sfrep-mcp\publish-pipeline\SfrepMcpServer.exe` (present). No SFREP cloud credentials needed (KB: local COM/app install).
- Comp apply precedent: `agent/sfrep_deep_fill.py::fill_comp_grid` writes via `sfrep_field_set_text` with `compType="SalesComparables"` and 1-based `compIndex` (2026-09-01 decision: compIndex 0 writes vanish). `SfrepPayloadPlanner.cs` structurally supports CompType/CompIndex but has zero canonical entries using them -> payload-only `comp.*` keys stay unmapped.
- Guinea pig `workfiles/by_address/6037_sundown_dr_fort_worth_tx_76114`: `metadata/artifact_selected_comps__...json` holds 6 selected comps (e.g. 21079679 / 1295 Roaring Springs / $218500 / 2026-05-27 / GLA 1356); `comps/selected_comps.json` absent; existing `sfrep/payload.json` (58 keys, 9/1) already has real subject identity + cost approach; prior `sfrep/report_full.pdf` (871,015 bytes, 9/1) from the pinned session.
- Rejected pigs: Winterstone selection blocked (`insufficient_qualifying_comps:2<3`, Stage 3 fence); Big Sky has no `sfrep/` dir (recommend-only follow-on).
- Decisions binding this contract: 2026-09-01 stage5 live demo + fail-closed apply + deterministic payload_fill (ImportMismo does not fill comps/cost); 2026-09-03 canonical naming + PDF+MISMO 2.6 GSE delivery format (delivery itself stays fenced); 2026-09-04 zero standing sessions + snapshot before close.
- Prior-cycle evidence: cycle 1 and 2 exec logs 0-byte after exactly 1202s (`coo/tmp/20260906-e2e-stage5-sfrep-wiring.exec.log`, `coo/live/...execute.live.log`); assessor verdicts in tangent file and `coo/tmp/20260906-e2e-stage5-sfrep-wiring.verdict.json`; diagnosis memo written 15:43 before the cycle-2 kill.
- Pinned transcript: `C:\Users\lkmot\.factory\sessions\-C-Users-lkmot-factory-context-code\3c80cca2-de30-481c-8be7-de57ba1df66e.jsonl`.

## Approach sketch
1. **Repo preflight (offline):** cwd = pipeline repo; confirm branch and the two dirty files; do not touch unrelated dirty state.
2. **Re-verify diagnosis:** confirm the memo's claims against current files (Sundown inputs unchanged). Leave the memo intact.
3. **Finish offline wiring:** verify the selection fallback feeds both MISMO and full-comps loads; add `--process-id` argparse to `tools/sfrep_apply.py` passing through to `McpStdioClient(process_id=...)`; wire a post-payload-fill comp-grid step (deep-fill `fill_comp_grid` or direct `sfrep_field_set_text`) so comps 1-3 get written during apply.
4. **Rebuild bundle (auto_apply=False):** regenerate Sundown `sfrep/payload.json`; immediately write `payload-inventory.json` to `coo/outcomes/` (artifact-first discipline: write each artifact the moment it exists).
5. **RAM hard gate:** measure free GB. If < 8, optionally stop agent-owned stray `SfrepMcpServer` processes only, remeasure once. Still red -> write session-safety.md (`deferred_ram_gate`), Outcome partial (environmental: yes), exit. No COM.
6. **If green, Phase B:** `SFREP_ALLOW_LIVE_APPLY=1` for this run only; launch/attach ONE agent-owned Appraise-It instance via explicit `--process-id`; run apply + comp-grid fill; MCP readback checklist; export `report_full.pdf`; write `apply.json` + `field-checklist.md`.
7. **Safety closeout:** RAM after; snapshot then dispose the agent-owned session per 2026-09-04 policy; never call deliver; never touch user instances.
8. **Write-back:** tangent Outcome + residual recommend-only list (delivery, Stage 3/4, C# map hole, coo-loop 1202s crash class, Big Sky Stage 5, image MCP gaps).

### Executor constraints
- SFREP COM authorized ONLY for this tangent's single Phase B proof session, and only after the RAM gate is green.
- Prefer existing tools: `generate_forms_prefill_bundle`, `tools/sfrep_apply.py`, `agent/sfrep_deep_fill.py`, `tools/e2e_validate.py` dry-run helpers, sfrep-mcp field get / PDF create.
- Never call `sfrep_report_deliver`; never open a second concurrent agent session; never close or write into user-owned sessions.
- Stop after 2 same-class live apply failures post-Phase-A (escalate_if) - no thrash loops.
- Write every artifact to disk as soon as it exists; expect the 1200s stage timeout and defend against it by finishing Phase A first.


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
run_started: 2026-09-06T16:07:36-05:00
