=== PROBE ===
# Probe: 20260906-sales-outreach-ledger-hygiene
revalidate_after: 2026-10-06
checks:
  - check: ledger step sdr-9800 still closed as retired and blocker still absent
    command: python -c "import json;d=json.load(open(r'C:\Users\lkmot\.factory\knowledge\project-ledger.json',encoding='utf-8'));p=[x for x in d['projects'] if x['id']=='sales-outreach'][0];s=[x for x in p['next_steps'] if x['id']=='sales-outreach:sdr-9800'][0];print(s['status'],s['completed_at'],[b['id'] for b in p['blockers']])"
    expect: "done 2026-09-06T20:17:10Z ['manyreach-auth']  (step still done, timestamp intact, sdr-9800 blocker absent, manyreach-auth still tracked)"
  - check: registry sales_emails still retirement-framed with no deploy-recover wording
    command: python -c "import json;P=r'C:\Users\lkmot\.factory\knowledge\workstream-registry.json';d=json.load(open(P,encoding='utf-8'));w=[x for x in d if x['workstream']=='sales_emails'][0];t=open(P,encoding='utf-8').read();print(w['status'],w['last_checked'],'deploy-framing-present' if 'needs Docker deploy' in t else 'deploy-framing-gone')"
    expect: "partial 2026-09-06 deploy-framing-gone"
  - check: decisions.jsonl line 57 still records the APPLIED retirement
    command: python -c "import json;L=open(r'C:\Users\lkmot\.factory\knowledge\decisions.jsonl',encoding='utf-8').read().splitlines();d=json.loads(L[56]);print(d['timestamp'],'applied' if 'Applied sdr-9800 retirement' in d['decision'] else 'MISSING',len(d.get('artifacts',[])))"
    expect: "2026-09-06T20:17:10Z applied 6"
  - check: timestamped raw-byte backups still exist beside both files
    command: Get-ChildItem "C:\Users\lkmot\.factory\knowledge\*.20260906T201233Z.bak" | Select-Object -ExpandProperty Name
    expect: project-ledger.json.20260906T201233Z.bak and workstream-registry.json.20260906T201233Z.bak both listed
  - check: retirement evidence still resolves and old workspace copy still absent
    command: python -c "import os;P=[r'C:\Users\lkmot\factory-context\motto-sales-engine\docs\kill-list.md',r'C:\Users\lkmot\factory-context\archive\sales-stack-2026-09-01\motto-sdr-agent',r'C:\Users\lkmot\.factory\specs\2026-09-06-unscopable-do-not-recover-9800.md',r'C:\Users\lkmot\motto-sdr-agent'];print([os.path.exists(p) for p in P])"
    expect: "[True, True, True, False]  (K1 kill-list, archive tree, unscopable spec all present; retired workspace copy NOT resurrected)"
  - check: full independent suite still passes
    command: python C:\Users\lkmot\factory-context\code\fleet-triage\coo\tmp\validate-20260906-sales-outreach-ledger-hygiene.py
    expect: "RESULT: ALL CHECKS PASSED (exit 0)"
verdict_on_last_run: PASS 2026-09-06 (validator re-executed all done-when items independently, 53/53 PASS; suite at coo/tmp/validate-20260906-sales-outreach-ledger-hygiene.py)
