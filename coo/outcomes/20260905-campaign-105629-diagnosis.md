# Diagnosis — zero replies on ManyReach campaign 105629 (SFR Buyers DFW — Batch 2)

Scoping/executor run: 2026-09-05 (COO tangent `20260905-campaign-105629-review`).
All live numbers below were read via the ManyReach MCP (`campaign/get_by_id`,
`campaign/stats_by_id`, `campaign/get_sequences_by_id`, `sequence/get_followups_by_id`,
`message/get`) on 2026-09-05 unless a file path is cited. Read-only: nothing was sent,
paused, patched, enrolled, or deleted during this work.

## Headline state (live 2026-09-05)

| Field | Value |
|---|---|
| Campaign | 105629 — "SFR Buyers DFW — Batch 2 — Aug 3" |
| Status | **Running** (created 2026-08-03T19:01Z, still dripping) |
| Prospects | 778 total / **298 active** |
| Sent (headline) | 335 |
| Opens (headline) | 15 (4.5% of 335) |
| Clicks | 12 |
| Bounces | 1 |
| Replies (headline) | 0 |
| Daily limit | 300/campaign, ramp +15% toward 300 |
| Senders | 15 across mottooutreach.com / txvalue.co / appraisalval.co |
| textOnlyEmails | **false** (HTML), trackOpens=true, trackClicks=true |
| replyTo | lkmotto@gmail.com |

Message-surface reality: `campaign/stats_by_id` sent series sums to **1,137 actual
message sends** (initial + followups) across 2026-08-03..09-04. The headline sentCount
(335) counts initial touches only; prospects have received up to 5 messages each. The
reply surface (`message/get type=Reply`) holds **1 row total** for this campaign and it
is an undeliverable/mailbox-full DSN (s2cp.com, 2026-08-18) — **0 human replies across
1,137 sends**.

Per-step counters (sequence 132731 + 133171):

| followupId | sent | opens | clicks | bounces | replies |
|---|---:|---:|---:|---:|---:|
| 202757 ("Re:" last-touch) | 193 | 2 | 0 | 0 | 0 |
| 202758 ("Re:" nudge) | 146 | 1 | 2 | 0 | 0 |
| 203418 ("Non-respondent" nudge) | 319 | 7 | 7 | 1 | 0 |
| 203419 ("Non-respondent" last-touch) | 135 | 0 | 4 | 0 | 0 |

## Dominant failure hypothesis: template mechanics + presentation (inbox-ignore / low trust)

**Locked hypothesis: the campaign's copy mechanics and presentation, not deliverability
alone and not list validity alone, are the dominant cause of zero replies.** The
template that generated 1,137 sends carries syntax the platform's own creation guards
now refuse, and its presentation (HTML + tracking + signature link) is the low-trust
pattern the fleet's own A/B verdict moved away from.

Evidence, each independently checkable:

1. **Unsupported `{abtest|...}` block in the live subject.** Live subject is
   `{abtest|{{FIRST_NAME}}, quick question|{{FIRST_NAME}} — {{COMPANY}}|DFW appraisals — {{FIRST_NAME}}|}`.
   `{abtest|...}` is not supported ManyReach syntax (only `{|...|}` spintax is). The
   identical block on control arm 109964 was diagnosed as the likely cause of that
   campaign's zero-queue stall (`motto-sales-engine/docs/backlog.md` B2,
   `data/verdicts/ab_test_verdict*.json`), and `campaign_create.py` now mechanically
   refuses it (`docs/runbooks/campaign-template-preconditions.md`). What it does on an
   already-running template is not fully observable from the API, but at minimum
   subject rendering/testing behavior is undefined — and at worst it suppresses the
   queue. Either way, every prospect's subject line comes from a construct the vendor
   does not support.
2. **Unsupported Jinja conditional in the body.** The body contains
   `{% if JOB_POSITION %}...{% endif %}` — the same class the creation guards refuse
   ("silently blocks sends", arm-A lesson). Undefined rendering behavior on the most
   personalized line of the opener.
3. **Presentation is the exact low-trust pattern the fleet already rejected.**
   `textOnlyEmails=false` with open+click tracking, versus the A/B/C verdict-era move
   to plain peer text (arms B/C: `textOnlyEmails=true`; wave-1 templates
   `docs/templates/wave-1/`). Observed click activity is mostly the tracked Gravatar
   signature link (clickDetails show `gravatar.com/lkmotto`), inflating clickCount to
   near-parity with opens (12 vs 15) — clicks here are signature-link artifacts, not
   CTA engagement.
4. **Zero human replies across all five touches with working infrastructure.** The
   pipeline demonstrably works: 1,137 sends, opens recorded (15 headline / 18 in the
   daily series), clicks recorded, exactly 1 bounce, and one DSN synced into the reply
   surface. Mail is flowing and being received; nothing is coming back. Copy that
   cannot earn an open on 95.5% of deliveries and earns no reply on any of 1,137
   placements is failing at the message level.
5. **The template would not pass today's own gates.** A fresh create with this
   subject/body is refused (`{abtest`, `{%`). Continuing to drip it from the legacy
   slot means every new send inherits the defect class the engine already outlawed.

## Secondary: audience/ICP misfit for national institutional SFR panels

Not dominant, but real, and it caps any fix's ceiling:

- Recipients visible in sent samples are **national institutional SFR operators** —
  Invitation Homes, Progress Residential, Tricon, Amherst, Home Partners, Roofstock,
  RangeWater, Second Avenue — with executive/corporate titles. The offer (one licensed
  residential appraiser in Trophy Club, 48-hour turn, direct, no AMC) is a
  vendor-panel pitch into procurement processes built for national coverage.
- The pool comes from the surround institutional map (`data/surround/surround-queue.json`,
  SFR Institutional domains mapped to campaigns [105629]: Invitation Homes, Progress
  Residential, etc.), the same sourcing family that produced the surrounding
  zero-reply channels (B4: 642 surround deliveries, 0 replies).
- 480 of 778 prospects have silently left "active" (298 active), consistent with
  list fatigue/exhaustion mechanics, and per-prospect history shows up to 5 touches.

## Contributing: fleet deliverability headwind (not campaign-local bounce crisis)

- Fleet sender health at last report (2026-09-01/02,
  `data/reports/sender_report_2026-09-01_post.json`,
  `sender_report_warmup_off_check.json`): **15 of 17 senders classified
  bounced/tmp_bounce**; bounce audit (`data/audits/2026-09-01/sender_bounce_audit.json`)
  ties the three outreach domains to a shared third-party bulk-mail IP pool.
- Campaign-local hard bounces are only 1, so "everything bounces" is **not** the story.
  But low opens (4.5%) cannot decompose into "inbox placement vs ignored" from inside
  the API — no placement data exists. A degraded fleet plausibly contributes to
  spam-foldering and therefore to the open and reply drought.
- The campaign runs `dailyLimit=300` against senders whose warmup ceilings are
  20-30/day — aggressive for the fleet's health state.
- Constraint note: ManyReach-side dailyLimit 300 vs the engine's quota calibration
  viewing this campaign at daily_cap 40 (`data/reports/quotas-live-calibration.json`) —
  the guardrail and the platform disagree; nothing in this diagnosis reconciles them
  (out of scope), but any approved relaunch must pick one number deliberately.

## What would change the ranking (falsifiers)

- If a raw SMTP/DSN sweep showed mass soft-bounce or deferral behind the "sent"
  counters, deliverability would outrank copy. Not observed: bounceCount=1 and the one
  DSN on the reply surface is a recipient-mailbox-full error.
- If opens were actually much higher than the tracking pixel suggests (text-heavy
  clients block pixels), the "inbox-ignore" story weakens — but the clickCount
  parity with opens and 0 replies on 1,137 sends still stand on their own.
- If reply capture were the problem (replies landing only in Luke's mailbox), the
  surface would undercount. The known capture boundary
  (`docs/replies/reply-capture-diagnosis-2026-09-02.md`) is real but demonstrated once
  for a single out-of-ICP reply; it cannot explain 1,137 silent sends fleet-wide.

## Recommendation (recommendation only — hard fence, no execution)

1. **Pause campaign 105629** pending operator approval; it is a compliant-template
   legacy (2026-09-02 sweep: PASS) so it was untouched by the protective pauses, but
   it carries unsupported syntax the create path now refuses and keeps dripping a
   480-stale institutional pool. Do not patch it in place (it is pre-mission legacy;
   patching extends its life against the backlog disposition rule).
2. **Do not re-run this audience.** Any approved next test uses wave-1-style local /
   operator-tier selection from the unenrolled CRM tiers, not the exhausted surround
   institutional map.
3. **Ship copy only as new paused drafts** cloned from the wave-1 patterns, after
   sender-health (B1) shows green-enough and the compliance sweep re-verifies PASS.
   Fix drafts live alongside this memo: `20260905-campaign-105629-fix-drafts.md`
   plus `fix-variant-a.*` / `fix-variant-b.*`.
4. Route the deliverability headwind to backlog **B1** (vendor support ask vs sender
   domain rotation) — Tier-B, operator decision; out of scope here.

## Evidence pointers

- Live snapshot + classification: `20260905-campaign-105629-evidence.json` (this folder)
- Template compliance sweep (105629 = PASS):
  `motto-sales-engine/docs/compliance/compliance-sweep-2026-09-02.md`
- Reply-capture boundary: `motto-sales-engine/docs/replies/reply-capture-diagnosis-2026-09-02.md`
- Arm-A `{abtest}` lesson + create guards:
  `motto-sales-engine/docs/runbooks/campaign-template-preconditions.md`,
  `motto-sales-engine/data/verdicts/ab_test_verdict.json`
- Fleet deliverability: `motto-sales-engine/data/reports/sender_report_2026-09-01_post.json`,
  `motto-sales-engine/data/audits/2026-09-01/sender_bounce_audit.json`
- Compliant copy reference: `motto-sales-engine/docs/templates/wave-1/`
- Surround sourcing map: `motto-sales-engine/data/surround/surround-queue.json`
