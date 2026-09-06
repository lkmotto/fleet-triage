# Validator re-execution of done-when checks for tangent 20260905-tangents-ledger-hygiene.
# READ-ONLY: parses live file, backup, decisions.jsonl, and stub. Writes nothing.
import json, os, glob, sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KDIR = r"C:\Users\lkmot\.factory\knowledge"
LIVE = os.path.join(KDIR, "tangents.json")
DEC  = os.path.join(KDIR, "decisions.jsonl")
STUB = r"C:\Users\lkmot\factory-context\code\fleet-triage\tangents\20260905-tangents-ledger-hygiene.md"

results = []  # (kind, name, ok, detail)

def check(kind, name, ok, detail):
    results.append((kind, name, bool(ok), detail))

# --- 1. Backup artifact (done-when 1) ---
baks = sorted(glob.glob(os.path.join(KDIR, "tangents.json*.bak")))
check("HARD", "A1 backup exists beside live file", len(baks) >= 1,
      ", ".join(os.path.basename(b) for b in baks) or "NONE")
bak_path = baks[-1] if baks else None
bak = None
if bak_path:
    try:
        with open(bak_path, encoding="utf-8") as f:
            bak = json.load(f)
        check("HARD", "A2 backup parses as JSON (readable)", True, bak_path)
    except Exception as e:
        check("HARD", "A2 backup parses as JSON (readable)", False, f"{type(e).__name__}: {e}")

bp = bak.get("pending", []) if bak else []
bc = bak.get("completed", []) if bak else []
bak_pend_completed = sum(1 for e in bp if isinstance(e, dict) and e.get("status") == "completed")
check("HARD", "A3 backup pending rows all status=completed (misfile story)", len(bp) == bak_pend_completed,
      f"backup pending={len(bp)} of-which-completed={bak_pend_completed} backup completed={len(bc)}")

# --- 2. Live file (done-when 2 & 3) ---
try:
    with open(LIVE, encoding="utf-8") as f:
        live = json.load(f)
    check("HARD", "B1 live file parses as JSON", True, LIVE)
except Exception as e:
    live = None
    check("HARD", "B1 live file parses as JSON", False, f"{type(e).__name__}: {e}")

if live is not None:
    keys = sorted(live.keys())
    expected_keys = sorted(["pending", "completed", "recent", "last_updated", "_note"])
    check("HARD", "B2 schema keys unchanged", keys == expected_keys, f"keys={keys}")

    lp, lc = live.get("pending", []), live.get("completed", [])
    check("HARD", "B3 pending contains only genuine work (len 0 expected)", len(lp) == 0,
          f"len(pending)={len(lp)}")
    cip = [e.get("id") for e in lp if isinstance(e, dict) and e.get("status") == "completed"]
    check("HARD", "B4 zero completed-in-pending", len(cip) == 0, f"completed-in-pending ids={cip[:5]}")
    bad_comp = [e.get("id") for e in lc if not (isinstance(e, dict) and e.get("status") == "completed")]
    check("HARD", "B5 all completed rows have status=completed", len(bad_comp) == 0,
          f"non-completed in completed array: {bad_comp[:5]}")
    check("HARD", "D1 len(pending)+len(completed)==74", len(lp) + len(lc) == 74,
          f"total={len(lp) + len(lc)} (pending={len(lp)} completed={len(lc)})")

    def ids(arr):
        return [e.get("id") for e in arr if isinstance(e, dict)]

    live_ids = ids(lp) + ids(lc)
    bak_ids = ids(bp) + ids(bc)
    dup_live = len(live_ids) != len(set(live_ids))
    dup_bak = len(bak_ids) != len(set(bak_ids))
    missing = set(bak_ids) - set(live_ids)
    extra = set(live_ids) - set(bak_ids)
    check("HARD", "C1 ids preserved vs backup (no loss, no dup)",
          (not missing) and (not extra) and (not dup_live) and (not dup_bak),
          f"live_unique={len(set(live_ids))} bak_unique={len(set(bak_ids))} "
          f"missing_vs_bak={sorted(missing)[:5]} extra_vs_bak={sorted(extra)[:5]} "
          f"dup_live={dup_live} dup_bak={dup_bak}")
    moved = set(ids(bp))
    check("HARD", "C2 every formerly-misfiled pending row now under completed",
          moved.issubset(set(ids(lc))),
          f"moved_count={len(moved)} not_in_live_completed={sorted(moved - set(ids(lc)))[:5]}")

    rl = live.get("recent"); rb = (bak or {}).get("recent")
    n = lambda x: len(x) if isinstance(x, list) else x
    check("SOFT", "D2 recent array untouched vs backup", n(rl) == n(rb),
          f"live_recent={n(rl)!r} bak_recent={n(rb)!r}")

    # --- 4. last_updated / _note (done-when 4) ---
    lu = live.get("last_updated")
    check("HARD", "E1 last_updated set", bool(lu), f"last_updated={lu!r}")
    note = live.get("_note", "") or ""
    note_ok = ("completed" in note.lower() and "pending" in note.lower())
    check("HARD", "E2 _note describes reconciliation", note_ok, f"_note={note[:240]!r}")
    check("SOFT", "E3 _note references backup filename",
          bak_path is not None and os.path.basename(bak_path) in note,
          f"backup={os.path.basename(bak_path) if bak_path else 'N/A'}")

# --- 5. Evidence trail (done-when 5) ---
row_hit = None
try:
    with open(DEC, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if "tangents" in line and ("02:10" in line or "47" in line or "reconcil" in line.lower()):
                row_hit = (i, line.strip()[:320])
                break
except Exception as e:
    row_hit = ("ERR", f"{type(e).__name__}: {e}")
check("HARD", "F1 decisions.jsonl carries reconciliation confirmation", row_hit is not None and row_hit[0] != "ERR",
      (f"line {row_hit[0]}: {row_hit[1]}" if row_hit else "no matching row"))

stub_note = False
try:
    with open(STUB, encoding="utf-8") as f:
        stub = f.read()
    stub_note = "## Outcome" in stub and "status:" in stub.split("## Outcome", 1)[1][:400]
except Exception:
    pass
check("HARD", "F2 done-when 5 (stub note OR decisions row)",
      stub_note or (row_hit is not None and row_hit[0] != "ERR"),
      f"stub_filled_outcome={stub_note} decisions_row={row_hit is not None and row_hit[0] != 'ERR'}")

# --- 6. Fence corroboration (informational) ---
mt = datetime.fromtimestamp(os.path.getmtime(LIVE))
exec_start = datetime(2026, 9, 5, 21, 15, 45)
check("SOFT", "G1 executor did not rewrite live file (mtime < exec start)", mt <= exec_start,
      f"live_mtime={mt.isoformat()} exec_start={exec_start.isoformat()} (local)")

hard_fails = [r for r in results if r[0] == "HARD" and not r[2]]
for kind, name, ok, det in results:
    tag = {"HARD": ("PASS" if ok else "FAIL"), "SOFT": ("ok" if ok else "info")}[kind]
    print(f"[{tag}] {name} | {det}")
print("SUMMARY:", "ALL HARD CHECKS PASS" if not hard_fails else f"{len(hard_fails)} HARD FAIL: {[f[1] for f in hard_fails]}")
sys.exit(0 if not hard_fails else 1)
