---
id: 20260905-gmail-intake-repair
status: done
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
## Contract (formalized post-hoc — work executed by scoping session before contract extraction; routed to assessment under operator dispatch approval)
- [ ] A repeatable order-intake scan path exists and is verified: scan script/config on disk, successful run returning order metadata only (no message bodies), JSON-valid
- [ ] The operative path documented: which tool/MCP it uses and how the heartbeat consumes it
- [ ] Zero sends; metadata only; no Doppler credential changes

## Out of scope (unchanged hard fences)
- Reading or sending email content; new secrets; automating sends

[route: operator-formalized; status advanced to assess]

## Assessor verdict
=== VERDICT: DONE === All three done-when items artifact-verified and independently reproduced (scan re-run exit 0, metadata-only, JSON-valid; mcp.json single-key diff vs sha256-matched backup); zero failed cycles.

## Validator
=== VALIDATION: PASS === value:unblocks_revenue; score:5; Independent live re-run exit 0 (SCAN_OK 201/5, ids-only privacy fence held in my own execution); 16/16 static checks incl. mcp.json single-key diff vs sha256-matched backup; 4 blind-cycle reports corroborated; zero failed cycles.
