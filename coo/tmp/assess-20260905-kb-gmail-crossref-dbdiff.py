"""Read-only assessor check: diff backup DB vs live memory.db across all kb_* tables.

Proves the tangent's only data change was the single intended kb_credentials label rename.
"""
import hashlib
import sqlite3

BACKUP = r"C:\Users\lkmot\.factory\memory.db.bak-20260906T025300Z"
LIVE = r"C:\Users\lkmot\.factory\memory.db"

with open(BACKUP, "rb") as f:
    print("backup sha256:", hashlib.sha256(f.read()).hexdigest().upper())

TABLES = ["kb_credentials", "kb_capabilities", "kb_services", "kb_deprecations", "kb_error_patterns"]

bak = sqlite3.connect(f"file:{BACKUP}?mode=ro", uri=True)
liv = sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True)
bc, lc = bak.cursor(), liv.cursor()

for t in TABLES:
    b_rows = sorted(bc.execute(f"SELECT * FROM {t}").fetchall())
    l_rows = sorted(lc.execute(f"SELECT * FROM {t}").fetchall())
    if b_rows == l_rows:
        print(f"{t}: IDENTICAL ({len(b_rows)} rows)")
    else:
        print(f"{t}: DIFFERS (backup {len(b_rows)} rows, live {len(l_rows)} rows)")
        b_set, l_set = set(map(str, b_rows)), set(map(str, l_rows))
        for r in sorted(b_set - l_set):
            print("  only-in-backup:", r)
        for r in sorted(l_set - b_set):
            print("  only-in-live:  ", r)

bak.close()
liv.close()
