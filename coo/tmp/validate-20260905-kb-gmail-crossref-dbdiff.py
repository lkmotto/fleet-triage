"""Validator: read-only diff of kb_* tables between pre-fix backup and live memory.db.

Prints only guidance/metadata columns; never prints credential values.
"""
import sqlite3

BACKUP = r"C:\Users\lkmot\.factory\memory.db.bak-20260906T025300Z"
LIVE = r"C:\Users\lkmot\.factory\memory.db"

CRED_META = "what, doppler_project, doppler_config, key_name"


def connect(path):
    uri = "file:" + path.replace("\\", "/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_names(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]


def main():
    bak = connect(BACKUP)
    liv = connect(LIVE)

    print("=== kb_credentials metadata diff (backup -> live) ===")
    q = f"SELECT {CRED_META} FROM kb_credentials ORDER BY key_name"
    bak_rows = {tuple(r) for r in bak.execute(q)}
    liv_rows = {tuple(r) for r in liv.execute(q)}
    for r in sorted(bak_rows - liv_rows):
        print("  REMOVED:", r)
    for r in sorted(liv_rows - bak_rows):
        print("  ADDED:  ", r)
    n_changes = len(bak_rows ^ liv_rows)
    print("  changed row count:", n_changes)

    print("=== full-row diff of other kb_* guidance tables ===")
    for t in ("kb_capabilities", "kb_services", "kb_deprecations", "kb_error_patterns"):
        if t not in table_names(bak) or t not in table_names(liv):
            print(f"  {t}: missing in one DB (backup present: {t in table_names(bak)})")
            continue
        cols = [r[1] for r in bak.execute(f"PRAGMA table_info({t})")]
        live_cols = [r[1] for r in liv.execute(f"PRAGMA table_info({t})")]
        if cols != live_cols:
            print(f"  {t}: SCHEMA differs")
            continue
        sel = ", ".join(f'"{c}"' for c in cols)
        b = {tuple(r) for r in bak.execute(f"SELECT {sel} FROM {t}")}
        l = {tuple(r) for r in liv.execute(f"SELECT {sel} FROM {t}")}
        if b == l:
            print(f"  {t}: identical ({len(l)} rows)")
        else:
            print(f"  {t}: DIFFERS (backup {len(b)} rows, live {len(l)} rows)")
            for r in sorted(b - l):
                print("    REMOVED:", str(r)[:200])
            for r in sorted(l - b):
                print("    ADDED:  ", str(r)[:200])

    print("=== row-count drift across all tables (names only; live-DB drift expected) ===")
    bt, lt = table_names(bak), table_names(liv)
    print("  tables only in backup:", sorted(set(bt) - set(lt)))
    print("  tables only in live:  ", sorted(set(lt) - set(bt)))
    for t in sorted(set(bt) & set(lt)):
        cb = bak.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        cl = liv.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if cb != cl:
            print(f"  {t}: {cb} -> {cl}")

    bak.close()
    liv.close()
    print("=== diff complete ===")


if __name__ == "__main__":
    main()
