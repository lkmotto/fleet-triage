---
id: YYYYMMDD-short-name
status: draft            # draft | queued | scoped | approved | running | done | parked | rescope
priority: high           # high | medium | low  (high = revenue-facing)
budget_cycles: 6
escalate_if: 2 failed cycles
origin: lkmot
scoped_by:               # coo-scoper | lkmot
---

# <Tangent title>

## Why
<Tie to revenue/ops goal.>

## Done when
- [ ] <Artifact-verified condition>

## Out of scope
- <Fenced item. Hard fences: mass email sends, deploys, DNS, deletion — end at recommendation.>

## Context
<Pointers: ledger blocker ids, KB queries, file paths, prior tangent failures.>

## Approach sketch
<Optional starter steps.>

---

## Executor instructions (pipeline section — do not edit above the divider when responding as executor)

You are the Executor. Work ONLY toward the Done-when items; the Out-of-scope fence is
hard — if the real path crosses it, STOP and write a rescope note instead of improvising.
If you discover the contract itself is wrong, STOP and say so (mid-flight bail).
Before exiting, append to this file:

## Outcome (filled by executor)
- status: success | partial | failed (environmental: yes/no)
- artifacts: <paths you produced>
- what was done: <2-4 lines>
- what remains: <or "nothing — done-when fully met">
- rescope note: <only if bailing>
