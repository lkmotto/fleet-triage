"""Read-only check of strategic_review same-day guard logic against real data.

Imports the module (no side effects at import: module body only sets sys.path
and constants) and evaluates the guard + dedup helpers. Writes nothing.
"""
import sys

sys.path.insert(0, r"C:\Users\lkmot\.factory\scripts")
import strategic_review as sr  # noqa: E402

# Guard: a run_id already recorded in proposals -> True
print("guard_20260809_expected_True:", sr._same_day_run_exists("strategic-review-20260809"))
print("guard_20260906_expected_False:", sr._same_day_run_exists("strategic-review-20260906"))

# Filed-run filter: last filed run should be 20260809 row (filed_urls=2)
runs = sr._filed_runs()
print("filed_runs_count:", len(runs))
print("last_filed_run_id:", runs[-1].get("run_id") if runs else None)
print("prior_proposals_count:", len(sr._prior_proposals()))

# Dedup set covers all runs' hypotheses
print("all_prior_hypotheses_count:", len(sr._all_prior_hypotheses()))

# Loader robustness: BOM on line 1 of proposals file
raw_first = sr._load_jsonl(sr.PROPOSALS_PATH)
print("loader_parsed_rows:", len(raw_first), "of 4 physical lines (BOM line tolerated?)")
