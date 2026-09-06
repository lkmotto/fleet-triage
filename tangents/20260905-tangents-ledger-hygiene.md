---
id: 20260905-tangents-ledger-hygiene
status: scoping
priority: medium
budget_cycles: 2
escalate_if: 1 failed cycle
origin: COO v1 audit (A1 evidence hygiene)
---

# Reconcile tangents.json pending-array misfiling

## Why
The tangent ledger shows 74 entries all with status "completed", but 47 sit inside
the "pending" array. The queue lies about backlog, which poisons scoping evidence.

## Done when
- [ ] Timestamped backup of tangents.json exists (same dir, .bak suffix)
- [ ] pending array contains only entries with genuine remaining work (expected: 0);
      completed array holds the rest — ids preserved, no data deleted
- [ ] Resulting file is valid JSON (verified by parse) and total entry count unchanged
- [ ] last_updated + _note updated to describe the reconciliation

## Out of scope
- Deleting any entries
- Changing the schema or the autonudge tooling that writes it
- Touching any other knowledge file
