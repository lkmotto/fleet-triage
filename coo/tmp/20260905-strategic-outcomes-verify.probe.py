"""One-shot DeepSeek API probe for the strategic-outcomes-verify tangent.

Prints diagnostics only; never prints the API key.
"""
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\lkmot\.factory\scripts")
from strategic_agents import _get_deepseek_key  # noqa: E402

key = _get_deepseek_key()
print("key_found", bool(key), "len", len(key) if key else 0)

payload = {
    "model": "deepseek-v4-pro",
    "messages": [{"role": "user", "content": 'Return exactly this JSON: {"ok": true}'}],
    "max_tokens": 4096,
    "temperature": 0,
    "response_format": {"type": "json_object"},
}
req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        print("status", r.status)
        print("content-type", r.headers.get("Content-Type"))
        print("content-encoding", r.headers.get("Content-Encoding"))
        print("body_len", len(body))
        print("body_prefix", body[:400])
        try:
            raw = json.loads(body)
            content = raw["choices"][0]["message"]["content"]
            print("outer_parse_ok choices", len(raw.get("choices", [])))
            print("content_prefix", content[:200])
            parsed = json.loads(content)
            print("inner_parse_ok", parsed)
        except Exception as e:
            print("PARSE_ERR", type(e).__name__, e)
except urllib.error.HTTPError as e:
    print("HTTPError", e.code)
    print("body", e.read()[:400])
except Exception as e:
    print("ERR", type(e).__name__, e)
