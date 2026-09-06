"""Validator read-only checks for 20260905-gmail-intake-repair. Writes nothing."""
import hashlib
import json
import os
import sys

FAILS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILS.append(name)
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))


def load_json_file(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw, json.loads(raw.decode("utf-8"))


# --- 1. Contract artifact: scan JSON (privacy fence: keys only id/threadId) ---
scan_path = r"C:\Users\lkmot\factory-context\code\fleet-triage\coo\outcomes\20260905-gmail-intake-repair-scan.json"
raw, scan = load_json_file(scan_path)
check("outcome artifact JSON-valid", True, f"{len(raw)} bytes")
check("outcome ok=true", scan.get("ok") is True, str(scan.get("ok")))
check("outcome path=composio-rest", scan.get("path") == "composio-rest", str(scan.get("path")))
check("outcome result_count>0", scan.get("result_count", 0) > 0, f"result_count={scan.get('result_count')}")
msgs = scan.get("messages", [])
keys_ok = all(set(m.keys()) <= {"id", "threadId"} for m in msgs) and len(msgs) > 0
check("privacy fence: message objects only id/threadId", keys_ok, f"{len(msgs)} messages")
banned = ("body", "snippet", "payload", "subject", "headers")
no_content = not any(k in json.dumps(scan).lower() for k in banned)
check("no body/snippet/subject content anywhere in artifact", no_content)

# --- 2. Heartbeat memory cache: exists and same shape ---
mem_path = r"C:\Users\lkmot\.factory\automations\autonudge-loop\memory\gmail-scan-latest.json"
exists = os.path.isfile(mem_path)
check("memory/gmail-scan-latest.json exists", exists)
if exists:
    _, mem = load_json_file(mem_path)
    mkeys = all(set(m.keys()) <= {"id", "threadId"} for m in mem.get("messages", []))
    check("memory cache ok=true + privacy shape", mem.get("ok") is True and mkeys,
          f"result_count={mem.get('result_count')} checked_at={mem.get('checked_at')}")

# --- 3. mcp.json integrity + single-key diff vs backup ---
mcp = r"C:\Users\lkmot\.factory\mcp.json"
bak = r"C:\Users\lkmot\.factory\mcp.json.bak-20260905-intake-repair"
with open(mcp, "rb") as fh:
    cur_raw = fh.read()
check("mcp.json no BOM (first bytes '{' + newline)", cur_raw[:1] == b"{", f"first3={list(cur_raw[:3])}")
cur = json.loads(cur_raw.decode("utf-8"))
st = cur.get("mcpServers", {}).get("smithery-toolbox", {})
check("smithery-toolbox.disabled is false", st.get("disabled") is False, f"disabled={st.get('disabled')!r}")
check("smithery-toolbox url intact", st.get("url") == "https://mcp.smithery.run/ljm32901", str(st.get("url")))

with open(bak, "rb") as fh:
    bak_raw = fh.read()
sha = hashlib.sha256(bak_raw).hexdigest().upper()
expected_sha = "A042000FCF7BFE71C8DB2E2B7ACA810D0DAEBA0A0675C5BFDEB7A2E0FB1AB5DE"
check("backup sha256 matches proof doc", sha == expected_sha, sha)
bakj = json.loads(bak_raw.decode("utf-8"))


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, p))
        else:
            out[p] = v
    return out


fc, fb = flatten(cur), flatten(bakj)
changed = sorted([k for k in set(fc) | set(fb) if fc.get(k) != fb.get(k)])
check("exactly one key differs vs backup", changed == ["mcpServers.smithery-toolbox.disabled"], f"changed={changed}")

# --- 4. Scan script: no send/mark endpoints ---
script = r"C:\Users\lkmot\.factory\automations\autonudge-loop\gmail_intake_scan.py"
with open(script, "r", encoding="utf-8") as fh:
    src = fh.read()
bad_terms = [t for t in ("/send", "/modify", "/trash", "/labels", "removeLabelIds", "method: \"POST\"") if t in src]
proxy_post = "\"method\": \"POST\"" in src or 'method="POST"' in src
check("no send/mark/label endpoints in script", not bad_terms, f"bad_terms={bad_terms}")
check("script uses proxy POST execute endpoint only", proxy_post)

# --- 5. HEARTBEAT fallback wiring ---
hb = r"C:\Users\lkmot\.factory\automations\autonudge-loop\HEARTBEAT.md"
with open(hb, "r", encoding="utf-8") as fh:
    hbtxt = fh.read()
wires = [
    "Gmail intake fallback (no MCP needed)" in hbtxt,
    "gmail_intake_scan.py" in hbtxt,
    "doppler run -p auth-api -c prd" in hbtxt,
    "gmail-scan-latest.json" in hbtxt,
    "Exit 2" in hbtxt,
]
check("HEARTBEAT fallback block wired (command + exit semantics + cache path)", all(wires), f"bits={wires}")

print()
print(f"SUMMARY: {len(FAILS)} failed" + (f" -> {FAILS}" if FAILS else " -- ALL PASS"))
sys.exit(1 if FAILS else 0)
