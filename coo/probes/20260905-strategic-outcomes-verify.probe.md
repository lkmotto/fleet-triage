=== PROBE ===
# Probe: 20260905-strategic-outcomes-verify
revalidate_after: 2026-09-13
checks:
  - check: Unconditional outcomes append still present in strategic_review.py
    command: Select-String -Path C:\Users\lkmot\.factory\scripts\strategic_review.py -Pattern '_append_jsonl\(OUTCOMES_PATH'
    expect: one match (append block ~L352). Absent = append-fix regression; ledger outcomes-always-write claim becomes unfair.
  - check: Same-day guard logic still behaves (known id True, unknown id False)
    command: python C:\Users\lkmot\factory-context\code\fleet-triage\coo\tmp\20260905-strategic-outcomes-verify.guard-check.py
    expect: "guard_20260809_expected_True: True" and "guard_20260906_expected_False: False"
  - check: Proof-run log still shows upstream timeout failure (D3 evidence)
    command: Select-String -Path C:\Users\lkmot\factory-context\code\fleet-triage\coo\tmp\20260905-strategic-outcomes-verify.run.log -Pattern 'read operation timed out'
    expect: at least one match; proves the failure landed upstream of the append block (not append-missing).
  - check: Diagnostic still shows D1 starvation (finish_reason length, empty content)
    command: Select-String -Path C:\Users\lkmot\factory-context\code\fleet-triage\coo\tmp\20260905-strategic-outcomes-verify.diagnostic-rerun.out -Pattern 'finish_reason length|content_len 0'
    expect: both patterns match; upstream-LLM root-cause evidence intact.
  - check: D1/D3 markers still unfixed while follow-up tangent 20260906-fix-strategic-review-llm-truncation is open
    command: Select-String -Path C:\Users\lkmot\.factory\scripts\strategic_review.py -Pattern '"max_tokens": 4096'; Select-String -Path C:\Users\lkmot\.factory\scripts\strategic_agents.py -Pattern 'timeout=60'
    expect: both match while follow-up is open. If either is gone, the follow-up landed, then the outcomes-file check must flip to True.
  - check: Outcomes file existence state matches classification
    command: Test-Path C:\Users\lkmot\.factory\knowledge\strategic_outcomes.jsonl
    expect: False while follow-up tangent open (classified absence, not regression). After follow-up lands: True, and last row run_id matches strategic-review-YYYYMMDD of that run date.
  - check: No unauthorized drift on strategic_review.py (fence audit baseline)
    command: Get-Item C:\Users\lkmot\.factory\scripts\strategic_review.py | Format-List Length,LastWriteTime
    expect: Length 16054, LastWriteTime 2026-08-24 17:11:47, unless a newly authorized tangent patched it.
verdict_on_last_run: PASS 2026-09-06
