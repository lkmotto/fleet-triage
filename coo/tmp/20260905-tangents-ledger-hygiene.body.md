---
id: 20260905-tangents-ledger-hygiene
status: scoped
priority: medium
budget_cycles: 2
escalate_if: Verification fails and pending again contains status=completed rows that cannot be moved without id loss, schema change, or deletion; or backup artifact missing/unreadable
origin: COO v1 audit (A1 evidence hygiene)
scoped_by: coo-scoper
scoped_at: 2026-09-06
---
# Reconcile tangents.json pending-array misfiling

## Why
COO queue health depends on `tangents.json` telling the truth about backlog. Misfiling completed rows into `pending` poisons scoping evidence and re-dispatch decisions. This is ops integrity for the tangent/COO loop, not a customer-facing change.

## Done when
- [ ] Timestamped backup exists beside live file: `C:\Users\lkmot\.factory\knowledge\tangents.json.*.bak` (acceptable pattern includes `tangents.json.20260906T020828Z.bak`)
- [ ] Live file `C:\Users\lkmot\.factory\knowledge\tangents.json` has `pending` containing only genuine remaining work (expected `[]` / length 0 if no live backlog); every former `status=completed` row lives under `completed`; entry `id`s preserved; no entries deleted
- [ ] Live file parses as JSON; `len(pending) + len(completed) == 74` (or matches pre-change total if new rows appeared after scoping — prove with before/after counts)
- [ ] `last_updated` is set and `_note` explicitly describes the reconciliation (moved completed-out-of-pending; pending = live backlog only)
- [ ] Executor writes a short verification note under the fleet-triage tangent stub path `C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260905-tangents-ledger-hygiene.md` (status/result only; no schema edits) OR appends confirmation to the existing decision trail without altering other knowledge files beyond `tangents.json` if still dirty

## Out of scope
- Deleting any tangent entries
- Changing `tangents.json` schema keys (`pending` / `completed` / `recent` / `last_updated` / `_note`)
- Fixing autonudge/writer code that originally misfiled completed rows into `pending` (known residual bug; own tangent if pursued)
- Touching other knowledge files (`project-ledger.json`, capabilities DB, etc.) except optional one-line decision already present
- Mass email, deploys, DNS/network, or any data deletion

## Context (verified during scoping)
Checked 2026-09-06 on host path `C:\Users\lkmot\.factory\knowledge\`:

1. **Live `tangents.json` already reconciled**
   - Keys: `pending`, `completed`, `recent`, `last_updated`, `_note`
   - `pending`: **0** entries
   - `completed`: **74** entries, all `status=completed`
   - `recent`: 1 entry (historical/index; leave alone)
   - `last_updated`: `2026-09-06T02:08:48Z`
   - `_note` states one-time move of 47 `status=completed` rows from pending → completed and points at backup name
   - Total unique ids across pending∪completed: **74**; no cross-array duplicate ids; no completed-in-pending misfiles remain

2. **Backup artifact present (pre-reconcile evidence)**
   - Path: `C:\Users\lkmot\.factory\knowledge\tangents.json.20260906T020828Z.bak`
   - Size ~71673 bytes (live ~70901)
   - Backup parse: `pending=47` (all `status=completed`), `completed=27` → 47+27=74
   - This matches the stub's original complaint (47 completed mis-seated in pending)

3. **Precedent / prior attempt**
   - Stub `20260905-tangents-ledger-hygiene` originated from COO v1 audit A1
   - Repo stub file exists: `fleet-triage\tangents\20260905-tangents-ledger-hygiene.md`
   - `decisions.jsonl` line ~48 (`2026-09-06T02:10:04Z`) records: moved 47 completed rows pending→completed; pending 0; completed 74; ids preserved; backup named above; **writer bug not fixed**
   - Prior session failed the Scoper role by performing the write instead of returning a contract. **Difference this cycle:** Executor must treat work as **verify-first / repair-only-if-regressed**, not blind rewrite. No second mass move unless live state has re-diverged.
   - KB/harvester: no capability/service entry for tangents; no blocking error pattern specific to this file
   - `project-ledger.json` mentions tangents generically; no open ledger item requiring extra schema work

4. **Fence**
   - Residual writer bug that can reintroduce misfiling is explicitly out of scope (recommendation-only if observed)

## Approach sketch
1. Re-read live `tangents.json` and the newest `tangents.json*.bak` with a JSON parse; record counts: pending len, completed len, completed-in-pending count, total, id-set size.
2. **If already clean** (pending has zero `status=completed`, totals coherent, note/backup present): do not rewrite arrays; only ensure done-when evidence is recorded on the tangent stub markdown (or confirm decision row) and mark this tangent complete.
3. **If regressed** (pending again holds `status=completed`):
   - Create a new timestamped backup in the same directory: `tangents.json.<UTC>.bak` before any write
   - Move only entries with `status=="completed"` from `pending` → `completed` (append; preserve full objects and ids)
   - Leave non-completed pending entries in `pending`
   - Do not touch `recent` except if required for validity; do not delete ids
   - Update `last_updated` (ISO UTC) and `_note` describing this repair
   - Re-parse and assert: no completed-in-pending; total entry count unchanged vs pre-move snapshot; valid JSON
4. Do not edit autonudge writers in this contract.
5. Stop after one successful verify or one successful repair + verify; escalate on id loss, parse failure, or inability to backup.

