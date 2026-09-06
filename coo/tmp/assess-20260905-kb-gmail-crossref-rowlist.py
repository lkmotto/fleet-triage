"""Read-only assessor check: list all kb_credentials rows (no secret values in this table)."""
import sqlite3

con = sqlite3.connect(r"file:C:\Users\lkmot\.factory\memory.db?mode=ro", uri=True)
cur = con.cursor()
print("columns:", [d[1] for d in cur.execute("PRAGMA table_info(kb_credentials)").fetchall()])
for row in cur.execute("SELECT what, doppler_project, doppler_config, key_name FROM kb_credentials ORDER BY rowid"):
    print(row)
con.close()
