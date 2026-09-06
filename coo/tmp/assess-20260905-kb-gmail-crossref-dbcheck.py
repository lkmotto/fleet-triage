"""Read-only assessor check: kb_credentials row state for tangent 20260905-kb-gmail-crossref."""
import sqlite3

NEW = "Composio API (OAuth custody: Gmail x2, Sheets, Docs, LinkedIn)"
OLD = "Composio API (OAuth custody)"

con = sqlite3.connect(r"file:C:\Users\lkmot\.factory\memory.db?mode=ro", uri=True)
cur = con.cursor()
print("new-label row count:", cur.execute("SELECT COUNT(*) FROM kb_credentials WHERE what = ?", (NEW,)).fetchone()[0])
print("old-label row count:", cur.execute("SELECT COUNT(*) FROM kb_credentials WHERE what = ?", (OLD,)).fetchone()[0])
print("composio row:", cur.execute(
    "SELECT what, doppler_project, doppler_config, key_name FROM kb_credentials WHERE key_name = 'COMPOSIO_API_KEY'"
).fetchall())
print("total kb_credentials rows:", cur.execute("SELECT COUNT(*) FROM kb_credentials").fetchone()[0])
print("tables:", [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()])
con.close()
