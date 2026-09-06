"""Diagnose the strategic_review LLM failure: replicate the exact call with diagnostics.

Builds the same prompt strategic_review.py builds, calls DeepSeek with the same
params, and prints finish_reason / token usage / content lengths. Writes nothing.
"""
import json
import sys
import urllib.request

sys.path.insert(0, r"C:\Users\lkmot\.factory\scripts")
from strategic_wake import build_state_dump  # noqa: E402
from strategic_agents import _get_deepseek_key  # noqa: E402
from strategic_review import build_prompt, _prior_proposals, REVIEW_AGENT  # noqa: E402

snapshot = build_state_dump()
prior = _prior_proposals()
snapshot["recent_strategic_proposals"] = prior
prompt = build_prompt(snapshot, prior)
print("prompt_chars", len(prompt))

payload = {
    "model": REVIEW_AGENT["model"],
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": REVIEW_AGENT["max_tokens"],
    "temperature": 0.4,
    "response_format": {"type": "json_object"},
}
req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {_get_deepseek_key()}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=90) as r:
    raw = json.loads(r.read().decode("utf-8"))

msg = raw["choices"][0]["message"]
print("finish_reason", raw["choices"][0].get("finish_reason"))
print("usage", json.dumps(raw.get("usage", {})))
reasoning = msg.get("reasoning_content") or ""
content = msg.get("content") or ""
print("reasoning_len", len(reasoning))
print("reasoning_tail", reasoning[-200:].replace("\n", " "))
print("content_len", len(content))
print("content_prefix", content[:200])
try:
    parsed = json.loads(content)
    print("inner_parse_ok keys", sorted(parsed.keys()))
except Exception as e:
    print("inner_parse_ERR", type(e).__name__, e)
