=== PROBE ===
# Probe: 20260905-scout-consumer-wiring
revalidate_after: 2026-09-13
checks:
  - check: scout blockers exist in project-ledger.json citing real event_ids and candidate keys
    command: python -c "import json;d=json.load(open(r'C:\Users\lkmot\.factory\knowledge\project-ledger.json',encoding='utf-8'));print(json.dumps([{'project':p['id'],'id':b['id'],'evidence':b['evidence'],'since':b['since']} for p in d['projects'] for b in p.get('blockers',[]) if b['id'].startswith('scout-')],indent=1))"
    expect: scout-ntreis (appraisal-pipeline), scout-timeout + scout-factory (memory-knowledge); evidence cites event_ids f82212d3178b / 534afb77993a,58fa680c8052 / 6ee600d48573,d7b606140412, key=<domain>::<type>, source=strategic_events.jsonl; since=2026-07-28
  - check: unconsumed metric false despite historical events
    command: python -c "import json;d=json.load(open(r'C:\Users\lkmot\.factory\knowledge\project-ledger.json',encoding='utf-8'));print(d['metrics']['_last_evidence']['scout_candidates_unconsumed'], d['metrics']['_last_evidence']['scout_candidate_keys'])"
    expect: "False ['factory::consolidation', 'ntreis::hardening', 'timeout::hardening']"
  - check: live refresh logic still consumes and clears (read-only)
    command: python C:\Users\lkmot\.factory\scripts\project_ledger.py --dry-run --force
    expect: scout_candidates_unconsumed=false in Evidence; 3 scout-evidence-refreshed lines + memory-knowledge:scout-orphan evidence-clear in Changes; footer DRY RUN (no writes)
  - check: historical event rows not deleted
    command: python -c "import io;print(sum(1 for l in io.open(r'C:\Users\lkmot\.factory\knowledge\strategic_events.jsonl',encoding='utf-8') if 'scout.candidate' in l))"
    expect: 5
  - check: outcomes stream covers the scout consumption path
    command: python -c "import io;print(sum(1 for l in io.open(r'C:\Users\lkmot\.factory\knowledge\ledger-outcomes.jsonl',encoding='utf-8') if 'scout-consumed' in l or 'scout-evidence-refreshed' in l))"
    expect: ">= 3 (initial consume 2026-09-06T16:08Z + refreshed re-run lines)"
  - check: ledger step memory-knowledge:scout-consumer stays done with outcome text
    command: python -c "import json;d=json.load(open(r'C:\Users\lkmot\.factory\knowledge\project-ledger.json',encoding='utf-8'));s=[s for p in d['projects'] for s in p.get('next_steps',[]) if s['id']=='memory-knowledge:scout-consumer'][0];print(s['status'], bool(s.get('outcome')))"
    expect: "done True"
verdict_on_last_run: PASS 2026-09-06
