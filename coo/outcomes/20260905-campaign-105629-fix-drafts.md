# Fix drafts — campaign 105629 (SFR Buyers DFW — Batch 2)

Companion to `20260905-campaign-105629-diagnosis.md`. Everything here is a **draft**:
nothing has been created, patched, paused, or sent on ManyReach. Shipping requires
explicit operator approval (hard fence).

## Recommendation summary

1. **Pause 105629** (operator approval required). It is template-compliant per the
   2026-09-02 sweep, which is exactly why it escaped the protective pauses — but it
   still carries unsupported `{abtest|...}` subject syntax and a `{% if %}` body
   conditional that the create path now refuses, and it keeps dripping a pool where
   480/778 prospects have already gone inactive. Do not patch it in place: it is
   pre-mission legacy, and the backlog disposition rule says patching extends the life
   of legacy campaigns instead of retiring them.
2. **Retire this audience from active use.** No re-enrollment into the exhausted
   surround institutional map. Any approved next test draws from unenrolled CRM tiers
   using the wave-1 local/operator-tier selection pattern (`scripts/wave_ops.py plan`
   already enforces reply-ICP + suppression + overlap checks).
3. **Rebuild copy as new paused Draft campaigns** from the variants below (both clone
   the reviewed wave-1 patterns, pass every `campaign_create.py` precondition, and land
   Paused with zero sends on creation per the guarded path). Activate only after the
   ship checklist passes.

## Ship checklist (all must be true before activation of any new draft)

- [ ] Operator approval for the specific campaign/audience/copy.
- [ ] Sender health (backlog B1) green-enough: bounce/tmp_bounce classification
      materially better than the 15/17 recorded 2026-09-01/02, or an approved
      sender-domain decision.
- [ ] Compliance sweep re-run: new campaign template verdict PASS.
- [ ] Engine quota gate aligned: pick ONE daily cap deliberately (ManyReach-side
      dailyLimit 300 vs engine calibration daily_cap 40 currently disagree).
- [ ] Audience drawn via `wave_ops.py plan` (suppression + reply-ICP + overlap clean),
      not the surround institutional map.

## Variant A — plain peer control (arm-B lineage)

Subject (`fix-variant-a.subject.txt`):

```
{{FIRST_NAME}} — {{COMPANY}} appraisals
```

Body (`fix-variant-a.body.html`) — verbatim reviewed wave-1 first-touch:

```html
<p>{{FIRST_NAME}},</p><p>I'm a licensed residential appraiser in Trophy Club covering DFW — I do acquisition and collateral appraisals for SFR operators and builders directly, no AMC layer, 48-hour turn.</p><p>If {{COMPANY}} handles appraisal coverage for its Texas portfolio, I'd like to send you a sample report and pricing. If someone else on your team manages that, I'm glad to go through them instead.</p><p>Luke Motto<br>Licensed Residential Appraiser, TX<br>Motto Appraisal Service<br>{{UNSUBSCRIBE_LINK}}</p>
```

Optional supported-spintax opener (only if variation is wanted; every option inside
`{|...|}` is vendor-supported):

```
{|I'm|This is|} Luke Motto — licensed residential appraiser in Trophy Club, covering DFW.
```

## Variant B — question subject peer (arm-C lineage)

Subject (`fix-variant-b.subject.txt`):

```
Who handles appraisal coverage for {{COMPANY}} in DFW?
```

Body (`fix-variant-b.body.html`):

```html
<p>{{FIRST_NAME}},</p><p>I'm a licensed residential appraiser in Trophy Club covering DFW. I do acquisition and collateral appraisals for SFR operators and builders directly — no AMC layer, 48-hour turn.</p><p>If {{COMPANY}} handles appraisal coverage in-house, I'd like to send you a sample report and pricing. If someone else on your team manages that, I'm glad to go through them instead.</p><p>Luke Motto<br>Licensed Residential Appraiser, TX<br>Motto Appraisal Service<br>{{UNSUBSCRIBE_LINK}}</p>
```

## Sequence guidance for any approved relaunch (drafts only)

- **Create settings:** `textOnlyEmails=true` (plain peer text), `trackOpens` and
  `trackClicks` OFF for the test cells — the A/B/C verdict family moved to text-only,
  and tracking pixels/links distort engagement and trust. Keep
  `{{UNSUBSCRIBE_LINK}}` in the body and Motto identity in `fromName` (guard-required).
- **Followups:** one nudge at 3 days (thread, "Re:" style, wave-1 second-touch
  pattern) and one last-touch at 7 days ("point me to the right contact" close).
  Cap at 3 total touches; the 5-touch 105629 pattern showed no engagement lift.
- **No** `{abtest|...}`, **no** `{% ... %}` conditionals anywhere; spintax only in the
  supported `{|...|}` form.
- **Evaluation gate:** declare a winner only at >=100 sends per variant or separated
  reply rates (B3 rule); reads via `message/get type=Reply` human candidates, never
  the stale headline `replyCount`.

## Explicitly not done here (fences)

- No pause/start/patch/archive call on 105629 or any campaign.
- No new campaign creation or prospect enrollment.
- No sender/DNS/domain changes (B1 remains a Tier-B operator decision:
  vendor support ask vs sender-domain rotation).
