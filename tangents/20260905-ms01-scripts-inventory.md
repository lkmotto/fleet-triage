---
id: 20260905-ms01-scripts-inventory
status: queued
priority: low
budget_cycles: 3
escalate_if: 1 failed cycle
origin: project-ledger proposed step (infrastructure:ms01-scripts-inventory)
---

# Inventory ms01-* scripts; map to workflows or mark archive-candidate

## Why
50+ ms01-* scripts in the flat code/ dir, mostly superseded by documented Proxmox
workflows. Script sprawl is noise that every session pays for. Ledger-classification
work that feeds the Minimalist Operations cull.

## Done when
- [ ] Inventory doc exists at coo/outcomes/ms01-scripts-inventory.md listing every
      ms01-* script with: purpose (1 line), mapped workflow (if any), and verdict
      keep / archive-candidate / unknown
- [ ] Counts summarized in the tangent file outcome block
- [ ] No script was moved, renamed, or deleted (inventory only)

## Out of scope
- Deleting or archiving anything (cull is a separate operator-approved tangent)
- Any ms01 server changes
