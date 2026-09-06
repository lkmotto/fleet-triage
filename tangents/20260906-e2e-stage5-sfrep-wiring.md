---
id: 20260906-e2e-stage5-sfrep-wiring
status: running
priority: high
budget_cycles: 6
escalate_if: 2 failed live Stage-5 apply cycles after diagnosis memo + preflight (RAM gate + payload rebuild) with the same root cause class; OR free RAM cannot stay ≥8 GB around a single agent-owned SFREP session; OR Appraise-It/sfrep-mcp unavailable on Legion after one install/path check
origin: pinned-session:3c80cca2-de30-481c-8be7-de57ba1df66e
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# e2e Stage 5: SFREP report assembly wired to real workfile data

## Why
Stage 5 (Export & Deliver → forms prefill / SFREP apply) is the last core domino for automated appraisal report production. Workfiles already carry tax/comps/context, but the open SFREP report still looks placeholder-empty. Closing the workfile→payload→live-fill gap is directly revenue-critical (core tier `appraisal-pipeline`: tax → comps → report without human back-office).

## Done when
- [ ] **Diagnosis artifact on disk:** `C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260906-e2e-stage5-sfrep-wiring-diagnosis.md` states (a) exact Stage-5 field data source chain with file paths, (b) why placeholders/blanks appear (gate vs mapping vs apply vs session), (c) guinea-pig slug + evidence cited from live files.
- [ ] **Payload rebuild proof:** regenerating Stage-5/forms bundle for the guinea pig produces `<workfile>/sfrep/payload.json` with real subject identity fields (street/city/state/zip at minimum match workfile) and a machine-readable field inventory at `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-payload-inventory.json` (key count, empty keys, unmapped/skipped categories).
- [ ] **Live apply proof (opt-in, one session):** with `SFREP_ALLOW_LIVE_APPLY=1` and configured `SFREP_APPLY_COMMAND`, one guinea-pig apply via `tools/sfrep_apply.py --mode apply` (or Stage 5 entry that uses the same bridge) fills the open report; export `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-apply.json` (apply stdout/MCP fill summary) plus `<workfile>/sfrep/report_full.pdf` (or twin under `coo/outcomes/…-report_full.pdf`).
- [ ] **Zero-placeholder field checklist diff:** `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-field-checklist.md` (and `.json` if scripted) lists required report fields checked via MCP readback (`sfrep_field_get_text` / status) after apply — **no blank/template/placeholder values** for the checklist’s required set (subject identity + structure core + at least comps 1–3 sale price/address/GLA if comps exist in workfile). Explicit “N/A — source absent in workfile” only allowed when diagnosis proves the source artifact is missing (not a wiring miss).
- [ ] **SFREP session safety record:** `coo/outcomes/20260906-e2e-stage5-sfrep-wiring-session-safety.md` logs free RAM before/after (≥8 GB free gate), single agent-owned session only, no delivery call, and session disposition (snapshot/close policy per 2026-09-04 decision: no idle standing sessions).
- [ ] **Write-back:** Outcome section on `tangents/20260906-e2e-stage5-sfrep-wiring.md`; if a durable gate bug was fixed (e.g. allow-flag wiring / misleading skip reason / mapping hole on required fields), note file paths changed. Recommend-only for delivery, Stage 3/4, image MCP gaps beyond checklist.

## Out of scope
- Stage 3 comp-certainty logic and Stage 4 TrueTracts repair/reseed (siblings `20260906-e2e-stage3-comp-certainty`, `20260906-e2e-stage4-truetracts-repair`)
- Any SFREP **delivery** to clients / TOTAL drop as a success criterion (`sfrep_report_deliver`, production client send) — hard fence
- Switching appraisal form software; building new MCP image-set tooling unless a checklist-required field is otherwise impossible (prefer document residual)
- Multi-order campaigns; second concurrent SFREP session; bulk live apply
- Mass email, production deploys, DNS/network changes, data deletion (hard fences)

## Context (verified during scoping)
- Machine: Legion; SFREP via `sfrep-mcp` at `C:\Users\lkmot\sfrep-integration\sfrep-mcp` (publish-pipeline exe used by `tools/sfrep_apply.py`).
- Stage 5 module chain: `agent/stages/stage5_export_deliver.py` → `stage10_forms_prefill.py` → `form_prefill_bridge.generate_forms_prefill_bundle` → optional `sfrep_apply`.
- Live-apply gate: `_auto_apply_enabled()` requires `SFREP_ALLOW_LIVE_APPLY` ∈ {1,true,yes,on} **and** non-empty `SFREP_APPLY_COMMAND`.
- `tools/run_e2e_336_pinyon.py` sets apply command only — live apply still off unless env opt-in.
- Docs: `docs/sfrep-migration-progress.md` — deterministic payload_fill is the e2e standard; ImportMismo does not fill comps/cost.
- Decisions: 2026-09-01 stage5 live demo + fail-closed apply; 2026-09-03 naming/delivery format; 2026-09-04 zero standing sessions + snapshot before close.
- Workfiles: many `sfrep/payload.json` already on disk; Winterstone is the documented full GSE reference; Sundown has prior `report_full.pdf` from pinned session; Big Sky lacks `sfrep/` today.
- Fleet-triage sibling Stage 4 contract path pattern and outcome locations under `coo/outcomes/`.
- KB: sfrep-mcp capability present; no sfrep credentials needed beyond local COM/app install.
- Pinned transcript: `C:\Users\lkmot\.factory\sessions\-C-Users-lkmot-factory-context-code\3c80cca2-de30-481c-8be7-de57ba1df66e.jsonl`

## Approach sketch
1. **Preflight (no live SFREP yet):** confirm RAM ≥8 GB free; pick guinea pig with richest on-disk inputs; inventory subject/comps/metadata vs existing `sfrep/payload.json`.
2. **Trace + diagnose:** read Stage5/10/bridge/apply path; run bundle generation with `auto_apply=False` (or env without allow flag); write diagnosis memo + payload inventory (prove gate vs thin mapping vs bad sources).
3. **Fix only wiring required for done-when:** e.g. document/runbook the allow-flag, correct misleading skip messaging, extend payload mapping for checklist-required blanks if sources exist; do not redesign Stage 3/4.
4. **Single live apply:** set `SFREP_ALLOW_LIVE_APPLY=1` for this run only; one agent-owned session; `sfrep_apply.py --mode apply` on guinea-pig payload; MCP readback checklist; export `report_full.pdf` + apply JSON.
5. **Safety closeout:** memory after; close/dispose agent session per policy (snapshot if needed); never call deliver.
6. **Write-back** tangent Outcome + residual recommend-only list (delivery, TT market fields, image gaps, Big Sky Stage 5 follow-on).

### Executor constraints
- Authorize SFREP COM only for this tangent’s single proof session.
- Prefer existing tools: `generate_forms_prefill_bundle`, `tools/sfrep_apply.py`, `tools/e2e_validate.py` dry_run helpers, sfrep-mcp field get/PDF create.
- If apply fails twice on the same class after diagnosis, stop and escalate with artifacts — no thrash loops.


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
run_started: 2026-09-06T14:56:51-05:00
