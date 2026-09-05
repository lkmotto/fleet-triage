---
id: 20260905-gmail-intake-repair
status: draft
priority: high
budget_cycles: 4
escalate_if: 2 failed cycles
origin: autonudge-carried-item (4 consecutive cycles, 20260904-05)
---

# Restore order-intake visibility (Composio Gmail proxy tool unavailable)

## Why
Order intake has been blind 4+ consecutive autonudge cycles: the session toolset lacks
`smithery-toolbox___execute` (the Composio Gmail proxy), and ToolSearch cannot load it.
No new-order scan is possible until intake is restored. This is the top of the revenue
funnel.

## Context
- Evidence: autonudge-loop reports 20260904T170134Z, 20260905T* (4 consecutive
  "UNAVAILABLE this session" entries)
- Known-good past state: the tool worked in prior sessions; something changed in the
  toolset registration or the smithery-toolbox MCP server (drift?)
- KB: `kb-query.py credential "gmail"`, `kb-query.py service "smithery"`,
  `kb-query.py error "toolset"`

## Out of scope
- Reading or sending actual email content (privacy fence) — restored intake is proven
  by a successful *scan* returning order metadata only
- Changing any Doppler credentials; new secrets = stop and report
- Automating sends (safety rule 2a — always fenced)
