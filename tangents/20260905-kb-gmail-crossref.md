---
id: 20260905-kb-gmail-crossref
status: scoping
priority: low
budget_cycles: 1
escalate_if: immediate
origin: COO v1 audit (scoper gap report: capability KB pointed to gmail, records under composio)
---

# Fix capability KB gmail/composio cross-reference

## Why
`kb-query.py capability/credential "gmail"` pointed nowhere useful during the intake
diagnosis; the operative records lived under "composio". A scoping session lost time
to a stale KB entry — exactly what the KB exists to prevent.

## Done when
- [ ] memory.db kb_capabilities/kb_credentials updated or cross-referenced so a
      "gmail" query returns the composio records (verified by running the query)
- [ ] Change documented in the outcome block

## Out of scope
- Any other KB reorganization; any credential value changes
