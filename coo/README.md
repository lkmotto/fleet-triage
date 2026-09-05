# coo/ — git-dictated tangent reloop harness

The COO loop: consumes approved tangents from `tangents/` and executes them
via headless Factory (`droid exec`), closing the propose-only gap.

## How a tangent flows

1. **Dictate** — copy `tangents/TEMPLATE.md`, fill the contract, open a PR.
   Chat dictation also works: Droid writes the file and opens the PR.
2. **Approve** — merge = authorized to run. Scope changes = new PR; the diff
   is the auditable rescope record.
3. **Execute** — the loop pulls, claims (`status: running`), and runs
   `droid exec -f tangents/<id>.md --auto medium`.
4. **Record** — outcome is appended to the tangent file, committed, pushed.
   `git log` = full history of every dictation, rescope, and result.

## Wiring it up (one-time)

1. Task Scheduler → Create Task:
   - Trigger: every 15 minutes
   - Action: `wscript.exe "C:\Users\lkmot\factory-context\code\fleet-triage\coo\run-hidden.vbs"`
2. Env overrides (optional, set on the task):
   - `COO_CYCLE_SECONDS` (default 900), `COO_AUTO_LEVEL` (default medium),
     `COO_MAX_CONSEC_FAILS` (default 3), `COO_WEBHOOK` (optional notify URL)

## Safety properties

- `--auto medium` only — tangents stop at approval queues, never cross them.
- Circuit breaker: 3 consecutive failed cycles → `coo/.breaker` file pauses
  the loop until an operator deletes it.
- Claim-before-run (`status: running` + push) prevents double execution.
- Per-tangent budget (`budget_cycles`) + escalation rule live in the contract;
  the executing session reads them from the same file.

## Ops surfaces it consumes at run time

The tangent file holds pointers, not data. The executing session expands them
live: `kb-query.py` (memory.db), `tangents.json`, `project-ledger.json`,
`strategic_proposals.jsonl`. Outcomes are written back to `tangents.json`,
`decisions.jsonl`, and (per AGENTS.md SOP write-back rule) the Notion SOPs DB.
