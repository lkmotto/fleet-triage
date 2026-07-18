"""Deep audit module — cross-references all truth sources before dispatch.

Builds an audit trail for every issue to give the handler droid the fullest
possible picture of "truth" before acting. Memory.db is one signal source but
vulnerable to stale facts, testing noise, and duplicates.

Truth sources checked per signal class:
  behavior-fix:    memory.db behavior_test facts, AGENTS.md section presence,
                   recent PASS facts for same probe, GitHub open issue dedup
  pipeline-blocker: memory.db recurring_error + blocker_narrative facts,
                    live-state verification (HTTP/SSH/Docker),
                    AGENTS.md service references, GitHub dedup
  cold-capability:  memory.db mention timestamps + fact counts,
                    live-state verification, AGENTS.md service references,
                    review-queue dedup
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

FACTORY = Path.home() / ".factory"
MEMORY_DB = FACTORY / "memory.db"
AGENTS_MD = FACTORY / "AGENTS.md"

# How old a fact can be before it's considered stale
STALE_THRESHOLD_DAYS = 7

# Surface tiers — determines audit behavior and issue framing
# Core: revenue-critical, fix immediately
# Infra: operational health, fix or consolidate
# Experimental: was tested, didn't stick — REMOVE, don't improve
# Dormant: previously active, now cold — audit for relevance
SURFACE_TIERS = {
    # Core (revenue)
    "sfrep-mcp": "core", "stagehand": "core", "doppler": "core", "bitwarden": "core",
    "appraisal-pipeline": "core", "sdr-agent": "core", "bidding": "core",
    "order-monitor": "core", "credential-grabber": "core",
    # Infra
    "hermes": "infra", "grafana": "infra", "otel": "infra", "tempo": "infra",
    "memory.db": "infra", "tailscale": "infra", "director": "infra",
    "mcp-server": "infra", "fleet-triage": "infra",
    "neo4j": "infra", "sourcebot": "infra",  # code graph + browser, active infra
    # Experimental (abandoned explorations)
    "n8n": "experimental", "windmill": "experimental",
    "optimization-db": "experimental",
}


def audit_item(item: dict) -> dict:
    """Run a deep cross-reference audit on a review-queue item.

    Returns an audit report dict with:
      confidence: "high" | "medium" | "low" | "stale"
      confidence_score: 0.0-1.0
      checks: list of (source, finding, weight) tuples
      narrative: plain-text audit trail for the issue body
    """
    payload = item.get("payload", {})
    signal_class = payload.get("signal_class", "unknown")

    if signal_class == "behavior-fix":
        return _audit_behavior_fix(item, payload)
    elif signal_class == "pipeline-blocker":
        return _audit_pipeline_blocker(item, payload)
    elif signal_class == "cold-capability":
        return _audit_cold_capability(item, payload)
    else:
        return _empty_audit("unknown signal class")


def _audit_behavior_fix(item: dict, payload: dict) -> dict:
    """Audit a behavior-fix signal: probe FAIL -> check AGENTS.md, recent PASS, dedup."""
    probe = payload.get("probe", "unknown")
    score = payload.get("score", 0)
    checks = []
    total_weight = 0
    corroboration = 0.0

    # Check 1: Is this probe still defined in behavior-test.py?
    bt_path = FACTORY / "scripts" / "behavior-test.py"
    if bt_path.exists():
        bt_text = bt_path.read_text(encoding="utf-8")
        if f'"{probe}"' in bt_text or f"'{probe}'" in bt_text:
            checks.append(("behavior-test.py", f"Probe '{probe}' still defined", 0.15))
            corroboration += 0.15
        else:
            checks.append(("behavior-test.py", f"Probe '{probe}' NOT FOUND — may have been removed", -0.3))
            corroboration -= 0.3
        total_weight += 0.15

    # Check 2: Is the target section still in AGENTS.md?
    agents_text = _read_agents_md()
    target_file = payload.get("target_file", "")
    target_section = payload.get("target_section", "")
    if target_section and target_section != "Unknown section":
        if target_section.lower() in agents_text.lower():
            checks.append(("AGENTS.md", f"Target section '{target_section}' exists", 0.15))
            corroboration += 0.15
        else:
            checks.append(("AGENTS.md", f"Target section '{target_section}' MISSING — may already be fixed", -0.2))
            corroboration -= 0.2
        total_weight += 0.15

    # Check 3: Has this probe PASSed recently? (counter-evidence)
    recent_pass = _memory_has_recent_pass(probe)
    if recent_pass:
        checks.append(("memory.db", f"Probe '{probe}' has recent PASS — signal may be stale", -0.4))
        corroboration -= 0.4
    else:
        checks.append(("memory.db", f"No recent PASS for '{probe}' — signal is genuine", 0.1))
        corroboration += 0.1
    total_weight += 0.4

    # Check 4: How fresh is the source fact?
    fact_age_days = _memory_fact_age("behavior_test", probe)
    if fact_age_days is not None:
        if fact_age_days < 1:
            checks.append(("memory.db", f"Signal is fresh (<1d old)", 0.1))
            corroboration += 0.1
        elif fact_age_days < 3:
            checks.append(("memory.db", f"Signal is {fact_age_days}d old — still relevant", 0.05))
            corroboration += 0.05
        elif fact_age_days > STALE_THRESHOLD_DAYS:
            checks.append(("memory.db", f"Signal is {fact_age_days}d old — possibly stale", -0.15))
            corroboration -= 0.15
        else:
            checks.append(("memory.db", f"Signal is {fact_age_days}d old", 0.0))
    total_weight += 0.15

    # Check 5: GitHub dedup (open issues for same probe)
    gh_dup = _github_has_open_issue(probe, "behavior-fix")
    if gh_dup is True:
        checks.append(("GitHub", f"Open issue exists for probe '{probe}' — DUPLICATE", -0.5))
        corroboration -= 0.5
    elif gh_dup is False:
        checks.append(("GitHub", "No open issue — signal is novel", 0.15))
        corroboration += 0.15
    else:  # None = could not check
        checks.append(("GitHub", "Could not check (gh auth unavailable)", 0.0))
    total_weight += 0.15

    confidence = _compute_confidence(corroboration, total_weight)

    # Build decision
    decision = _build_decision("behavior-fix", _surface_tier(probe),
                                confidence, None, None, checks, payload)

    return _build_audit_report(confidence, checks, decision=decision)


def _audit_pipeline_blocker(item: dict, payload: dict) -> dict:
    """Audit a pipeline-blocker: recurring error + live-state + service health."""
    domain = payload.get("domain", "unknown")
    sessions = payload.get("session_count", 0)
    checks = []
    total_weight = 0
    corroboration = 0.0

    # Check 1: How many corroborating memory.db facts?
    fact_count = _memory_fact_count("recurring_error", domain)
    blocker_count = _memory_fact_count("blocker_narrative", domain)

    # Check 0: Surface tier — determines framing
    tier = _surface_tier(domain)
    if tier == "experimental":
        checks.append(("tier", f"'{domain}' is EXPERIMENTAL — abandoned exploration, do not fix", -0.6))
        corroboration -= 0.6
        total_weight += 0.6
    elif tier == "core":
        checks.append(("tier", f"'{domain}' is CORE — revenue-critical, fix urgently", 0.3))
        corroboration += 0.3
        total_weight += 0.3
    elif tier == "infra":
        checks.append(("tier", f"'{domain}' is INFRA — operational health, fix or consolidate", 0.1))
        corroboration += 0.1
        total_weight += 0.1
    else:
        checks.append(("tier", f"'{domain}' is UNCLASSIFIED — audit for relevance", -0.1))
        corroboration -= 0.1
        total_weight += 0.1
    if fact_count > 0:
        weight = min(0.2, fact_count * 0.02)
        checks.append(("memory.db", f"{fact_count} recurring_error facts for '{domain}'", weight))
        corroboration += weight
        total_weight += weight
    if blocker_count > 10:
        checks.append(("memory.db", f"{blocker_count} blocker narratives — strong corroboration", 0.15))
        corroboration += 0.15
        total_weight += 0.15

    # Check 2: How frequently occurring? (sessions vs total sessions)
    total_sessions = _memory_total_sessions()
    if total_sessions > 0:
        freq = sessions / total_sessions
        if freq > 0.1:
            checks.append(("memory.db", f"Affects {sessions}/{total_sessions} sessions ({freq:.0%}) — high frequency", 0.1))
            corroboration += 0.1
        else:
            checks.append(("memory.db", f"Affects {sessions}/{total_sessions} sessions ({freq:.0%}) — moderate", 0.0))
        total_weight += 0.1

    # Check 2b: State freshness — when was this surface last observed?
    # This is informational context, not a confidence gate. An old observation
    # is still our best knowledge of current state — we just flag it as unverified.
    last_seen, first_seen = _memory_recurring_timestamps(domain)
    if last_seen:
        try:
            last_dt = datetime.fromisoformat(last_seen)
            age_days = (datetime.now() - last_dt).days
            if age_days <= 1:
                checks.append(("memory.db", f"State verified {age_days}d ago — current", 0.1))
                corroboration += 0.1
            elif age_days <= 14:
                checks.append(("memory.db", f"Last observed {age_days}d ago — likely current", 0.0))
            else:
                # State is old but still our best knowledge. Flag as unverified,
                # not untrustworthy. The decision engine treats this as one signal.
                checks.append(("memory.db", f"Last observed {age_days}d ago — state may have changed, unverified", -0.1))
                corroboration -= 0.1
            total_weight += 0.1
        except Exception:
            pass

    # Check 3: Live-state verification
    live_state = payload.get("live_state") or {}
    ls_status = live_state.get("status", "unchecked")
    if ls_status == "alive":
        checks.append(("live-state", f"Service '{domain}' is ALIVE — genuine error", 0.2))
        corroboration += 0.2
    elif ls_status == "dead":
        checks.append(("live-state", f"Service '{domain}' is DEAD — may be retired", -0.3))
        corroboration -= 0.3
    elif ls_status == "unreachable":
        checks.append(("live-state", f"Service '{domain}' UNREACHABLE — could be temporary", -0.05))
        corroboration -= 0.05
    else:
        checks.append(("live-state", "Not checked — adding uncertainty", -0.05))
        corroboration -= 0.05
    total_weight += 0.2

    # Check 4: Is this domain still referenced in AGENTS.md?
    agents_text = _read_agents_md()
    if domain.lower() in agents_text.lower():
        checks.append(("AGENTS.md", f"Domain '{domain}' still referenced — actively maintained", 0.1))
        corroboration += 0.1
    else:
        checks.append(("AGENTS.md", f"Domain '{domain}' NOT in AGENTS.md — possibly deprecated", -0.15))
        corroboration -= 0.15
    total_weight += 0.15

    # Check 5: Sample freshness
    samples = payload.get("samples", [])
    if samples:
        checks.append(("samples", f"{len(samples)} sample errors from sessions", 0.05))
        corroboration += 0.05
        total_weight += 0.05

    # Check 6: Docker health on ms01 (if applicable)
    if domain in ("n8n", "grafana", "hermes", "neo4j", "sourcebot", "windmill"):
        docker_status = _check_docker_on_ms01()
        if docker_status == "down":
            checks.append(("Docker", "Docker Desktop is DOWN on ms01 — explains service outages", -0.1))
            corroboration -= 0.1
        elif docker_status == "up":
            checks.append(("Docker", "Docker is running — service outage is specific", 0.05))
            corroboration += 0.05
        else:
            checks.append(("Docker", "Could not check Docker status", 0.0))
        total_weight += 0.1

    # Check 7: GitHub dedup
    gh_dup = _github_has_open_issue(domain, "pipeline-blocker")
    if gh_dup is True:
        checks.append(("GitHub", f"Open issue exists for '{domain}' — DUPLICATE", -0.5))
        corroboration -= 0.5
    elif gh_dup is False:
        checks.append(("GitHub", "No open issue — signal is novel", 0.15))
        corroboration += 0.15
    total_weight += 0.15

    confidence = _compute_confidence(corroboration, total_weight)

    # Build decision
    decision = _build_decision("pipeline-blocker", _surface_tier(domain),
                                confidence, None, live_state, checks, payload)

    return _build_audit_report(confidence, checks, decision=decision)


def _audit_cold_capability(item: dict, payload: dict) -> dict:
    """Audit a cold-capability signal: memory mention gap + live-state + deprecation."""
    name = payload.get("name", "unknown")
    days_cold = payload.get("days_cold", 0)
    checks = []
    total_weight = 0
    corroboration = 0.0

    # Check 0: Surface tier — determines framing
    tier = _surface_tier(name)
    if tier == "experimental":
        checks.append(("tier", f"'{name}' is EXPERIMENTAL — should be REMOVED, not revived", 0.5))
        corroboration += 0.5
        total_weight += 0.5
    elif tier == "core":
        checks.append(("tier", f"'{name}' is CORE — being cold is alarming", 0.3))
        corroboration += 0.3
        total_weight += 0.3
    elif tier == "infra":
        checks.append(("tier", f"'{name}' is INFRA — cold infra needs attention", 0.05))
        corroboration += 0.05
        total_weight += 0.05
    else:
        checks.append(("tier", f"'{name}' is UNCLASSIFIED — audit for relevance", -0.1))
        corroboration -= 0.1
        total_weight += 0.1

    # Check 1: How cold? (more days = stronger signal)
    if days_cold >= 7:
        checks.append(("memory.db", f"Surface cold for {days_cold}d — strong signal", 0.25))
        corroboration += 0.25
    elif days_cold >= 3:
        checks.append(("memory.db", f"Surface cold for {days_cold}d — moderate signal", 0.15))
        corroboration += 0.15
    else:
        checks.append(("memory.db", f"Surface cold for {days_cold}d — weak signal", 0.0))
    total_weight += 0.25

    # Check 2: AGENTS.md status (deprecated or active?)
    agents_text = _read_agents_md()
    if name.lower() in agents_text.lower():
        if "deprecated" in agents_text.lower() or "dead" in agents_text.lower():
            checks.append(("AGENTS.md", f"'{name}' is marked DEPRECATED in AGENTS.md", -0.3))
            corroboration -= 0.3
        else:
            checks.append(("AGENTS.md", f"'{name}' is ACTIVE in AGENTS.md — neglected, not retired", 0.15))
            corroboration += 0.15
    else:
        checks.append(("AGENTS.md", f"'{name}' NOT referenced — may be dead weight", -0.1))
        corroboration -= 0.1
    total_weight += 0.3

    # Check 3: Live-state verification
    live_state = payload.get("live_state") or {}
    ls_status = live_state.get("status", "unchecked")
    if ls_status == "alive" or ls_status == "running" or ls_status == "active":
        checks.append(("live-state", f"'{name}' is RUNNING — audit opportunity (not dead)", 0.2))
        corroboration += 0.2
    elif ls_status == "dead" or ls_status in ("stopped", "not_found", "archived"):
        checks.append(("live-state", f"'{name}' is CONFIRMED DOWN — decommission candidate", 0.15))
        corroboration += 0.15
    else:
        checks.append(("live-state", f"Unverified ({ls_status})", -0.05))
        corroboration -= 0.05
    total_weight += 0.2

    # Check 4: GitHub dedup
    gh_dup = _github_has_open_issue(name, "cold-capability")
    if gh_dup is True:
        checks.append(("GitHub", f"Open issue exists for '{name}' — DUPLICATE", -0.5))
        corroboration -= 0.5
    elif gh_dup is False:
        checks.append(("GitHub", "No open issue — novel signal", 0.1))
        corroboration += 0.1
    total_weight += 0.15

    # Check 5: Previous cold scan for same surface?
    prev_scan = _memory_has_recent_fact("cold_capability", name, days=7)
    if prev_scan:
        checks.append(("memory.db", f"Previously cold-scanned within 7d — may be a persistent gap", 0.1))
        corroboration += 0.1
    else:
        checks.append(("memory.db", "First time flagged", 0.0))
    total_weight += 0.1

    confidence = _compute_confidence(corroboration, total_weight)

    # Pro/con analysis for keep vs remove decision
    pc = _surface_pros_cons(name, _surface_tier(name), days_cold,
                             payload.get("live_state"),
                             payload.get("fact_count", 0))

    # Build decision with pro/con
    decision = _build_decision("cold-capability", _surface_tier(name),
                                confidence, pc, payload.get("live_state"),
                                checks, payload)

    return _build_audit_report(confidence, checks, pros_cons=pc, decision=decision)


def _surface_tier(name: str) -> str:
    """Determine the tier of a surface by name. Returns 'core'|'infra'|'experimental'|'unknown'."""
    name_lower = name.lower().replace("_", "-").replace(" ", "-")
    for key, tier in SURFACE_TIERS.items():
        if key in name_lower or name_lower in key:
            return tier
    return "unknown"


def _is_engine_dependency(name: str) -> bool:
    """Check if the engine itself depends on this surface to function.

    The engine shouldn't recommend removing surfaces it actively uses
    for auditing, memory, or decision-making. Self-referential validation
    prevents the engine from sawing off the branch it sits on.
    """
    key = name.lower().replace("_", "-").replace(" ", "-")

    # memory.db: the engine reads memory for signal
    if "memory" in key and (MEMORY_DB.exists() if "MEMORY_DB" in dir() else True):
        return True

    # neo4j: code graph + memory server used for deep context
    if "neo4j" in key:
        return True

    # parts-bin: recycler cache that informs engine decisions
    if "parts-bin" in key or "partsbin" in key:
        return (FACTORY / "knowledge" / "parts-bin.json").exists()

    # Doppler: engine uses it for auth
    if "doppler" in key:
        try:
            result = subprocess.run(
                ["doppler", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        return False

    # GitHub: engine queries it for dedup
    if "github" in key or "auth-sso" in key:
        return bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT"))

    return False


def _quantitative_decision(signal_class: str, tier: str, name: str,
                           confidence: tuple[str, float],
                           live_state: dict | None,
                           checks: list[tuple],
                           days_cold: int = 0,
                           fact_count: int = 0,
                           session_count: int = 0,
                           _retry: bool = False) -> dict:
    """Universal quantitative decision engine.

    Every audit check scores every action directly — no intermediate
    abstraction layer. Each check asks: "what does this finding tell us
    about whether we should fix / remove / consolidate / ... this surface?"

    The recommendation is the highest-scoring action, supported by
    specific audit findings cited in the reasoning. Every weight is
    anchored to a concrete check, not an abstract category.

    Returns dict with ranked actions, recommendation, differential
    reasoning, and markdown-formatted output.
    """
    level, score = confidence
    ls_status = live_state.get("status", "unknown") if live_state else "unknown"
    scoring_detail = {}  # action -> [(check_text, weight, source)]

    def _score_all():
        """Score every action by running every check against it.

        Each check produces a weight for each action based on what the
        finding implies about that action. A check may favor one action
        (+0.5) and oppose another (-0.4) simultaneously.
        """
        scores = {a: 0.0 for a in ACTIONS}
        detail = {a: [] for a in ACTIONS}

        for source, finding, weight in checks:
            abs_w = abs(weight)
            sig = 1 if weight >= 0 else -1

            if "DUPLICATE" in finding.upper() or "duplicate" in finding.lower():
                # Duplicate finding: dismiss is correct, everything else wastes effort
                _add("dismiss", f"Duplicate: {finding}", +0.4, source, detail, scores)
                _add("fix", f"Duplicate: {finding}", -0.3, source, detail, scores)
                _add("investigate", f"Duplicate: {finding}", -0.1, source, detail, scores)

            elif source == "tier":
                _score_tier_check(finding, detail, scores)

            elif source == "live-state":
                _score_livestate_check(finding, detail, scores)

            elif source == "Docker":
                _score_docker_check(finding, detail, scores)

            elif source in ("memory.db", "behavior-test.py", "AGENTS.md"):
                _score_truth_source_check(source, finding, weight, sig, abs_w,
                                          detail, scores)

            elif source == "GitHub":
                _score_github_check(finding, detail, scores)

            else:
                # Generic: weight favors fix (positive signal) or remove (negative)
                if sig > 0:
                    _add("fix", f"[{source}] {finding}", +0.1, source, detail, scores)
                    _add("dismiss", f"[{source}] {finding}", -0.05, source, detail, scores)
                else:
                    _add("dismiss", f"[{source}] {finding}", +0.05, source, detail, scores)
                    _add("fix", f"[{source}] {finding}", -0.1, source, detail, scores)

        # Post-processing: apply tier-based modifiers
        _apply_tier_post(tier, detail, scores)

        # Cross-cutting concerns: not specific surfaces, patterns across many.
        # "credential", "timeout", "path", "powershell" — investigate/consolidate.
        cross_cutting = any(kw in name.lower() for kw in (
            "credential", "timeout", "path", "powershell", "shell",
            "environment", "drift", "permission"))
        if cross_cutting and tier != "core":
            scores["consolidate"] += 0.15
            scores["fix"] -= 0.1
            scores["investigate"] += 0.05

        return scores, detail

    def _score_tier_check(finding: str, detail, scores):
        f = finding.lower()
        if "experimental" in f:
            # Default: experimental → remove/dismiss. But if recent ACTIVITY
            # (not just accumulated error volume) is detected, bias investigate.
            # High session_count with errors is historical signal, not recent engagement.
            has_recent_activity = (
                session_count < 50 and  # high volume = accumulated, not recent
                any("recent" in c[1].lower() or "alive" in c[1].lower()
                   or "restarted" in c[1].lower() or "revived" in c[1].lower()
                   for c in checks))
            if has_recent_activity:
                _add("investigate", finding + " (recent activity detected)", +0.4, "tier", detail, scores)
                _add("remove", finding, +0.3, "tier", detail, scores)
                _add("dismiss", finding, +0.1, "tier", detail, scores)
                _add("fix", finding, -0.3, "tier", detail, scores)
            else:
                _add("remove", finding, +0.5, "tier", detail, scores)
                _add("dismiss", finding, +0.4, "tier", detail, scores)
                _add("fix", finding, -0.5, "tier", detail, scores)
                _add("investigate", finding, -0.2, "tier", detail, scores)
                _add("consolidate", finding, -0.3, "tier", detail, scores)
        elif "core" in f:
            _add("fix", finding, +0.5, "tier", detail, scores)
            _add("remove", finding, -0.6, "tier", detail, scores)
            _add("dismiss", finding, -0.5, "tier", detail, scores)
            _add("escalate", finding, +0.2, "tier", detail, scores)
        elif "infra" in f:
            _add("fix", finding, +0.3, "tier", detail, scores)
            _add("consolidate", finding, +0.3, "tier", detail, scores)
            _add("remove", finding, -0.3, "tier", detail, scores)
        elif "unclassified" in f or "dormant" in f:
            _add("investigate", finding, +0.2, "tier", detail, scores)
            _add("remove", finding, +0.1, "tier", detail, scores)

    def _score_livestate_check(finding: str, detail, scores):
        f = finding.lower()
        # Hostile surface detection — 403, secure-browser, anti-automation
        hostile = any(kw in f for kw in (
            "403", "secure-browser", "anti-automation", "hostile",
            "fingerprint", "captcha", "bot-detection", "blocked by",
            "google secure", "rate-limit"))
        if hostile:
            # Hostile surface: NOT a fixable bug. Escalate to operator.
            _add("escalate", finding, +0.5, "live-state", detail, scores)
            _add("fix", finding, -0.3, "live-state", detail, scores)
            _add("dismiss", finding, -0.1, "live-state", detail, scores)
        elif "alive" in f:
            _add("fix", finding, +0.4, "live-state", detail, scores)
            _add("dismiss", finding, -0.3, "live-state", detail, scores)
            _add("investigate", finding, +0.2, "live-state", detail, scores)
        elif "dead" in f or "not_found" in f or "not found" in f:
            # Dead = no active surface. Remove and dismiss are equally valid.
            _add("remove", finding, +0.3, "live-state", detail, scores)
            _add("dismiss", finding, +0.3, "live-state", detail, scores)
            _add("fix", finding, -0.2, "live-state", detail, scores)
        elif "unreachable" in f or "cannot reach" in f or "timed out" in f:
            _add("investigate", finding, +0.2, "live-state", detail, scores)
            _add("remove", finding, +0.1, "live-state", detail, scores)
            _add("fix", finding, -0.1, "live-state", detail, scores)

    def _score_docker_check(finding: str, detail, scores):
        f = finding.lower()
        if "down" in f:
            _add("remove", finding, +0.1, "Docker", detail, scores)
            _add("fix", finding, -0.1, "Docker", detail, scores)
        elif "up" in f or "running" in f:
            _add("fix", finding, +0.1, "Docker", detail, scores)

    def _score_truth_source_check(source, finding, weight, sig, abs_w, detail, scores):
        """Score checks from truth sources (memory.db, behavior-test.py, AGENTS.md).

        Key insight: negative-weight checks MUST penalize fix, not just boost
        dismiss. Counter-evidence should reduce confidence in fixing.
        """
        finding_lower = finding.lower()
        if "not found" in finding_lower or "missing" in finding_lower or "not in" in finding_lower:
            _add("remove", f"[{source}] {finding}", +abs_w * 0.5, source, detail, scores)
            _add("dismiss", f"[{source}] {finding}", +abs_w * 0.3, source, detail, scores)
            _add("fix", f"[{source}] {finding}", -abs_w * 0.2, source, detail, scores)
        elif "still" in finding_lower or "exists" in finding_lower or "referenced" in finding_lower:
            _add("fix", f"[{source}] {finding}", +abs_w * 0.4, source, detail, scores)
        elif sig > 0:
            _add("fix", f"[{source}] {finding}", +abs_w * 0.3, source, detail, scores)
            _add("investigate", f"[{source}] {finding}", +abs_w * 0.1, source, detail, scores)
        else:
            # Negative-weight check: penalize fix AND boost dismiss.
            # Strong counter-evidence should meaningfully reduce fix confidence.
            # A check with weight -0.4 means "there's significant evidence
            # against this being a real problem" — fix should be penalized
            # by at least that much.
            _add("dismiss", f"[{source}] {finding}", +abs_w * 0.25, source, detail, scores)
            _add("fix", f"[{source}] {finding}", -abs_w * 0.8, source, detail, scores)
            _add("investigate", f"[{source}] {finding}", +abs_w * 0.05, source, detail, scores)

    def _score_github_check(finding: str, detail, scores):
        if "could not check" in finding.lower() or "unavailable" in finding.lower():
            return  # no signal
        elif "duplicate" in finding.lower() or "open issue exists" in finding.lower():
            _add("dismiss", finding, +0.5, "GitHub", detail, scores)
            _add("fix", finding, -0.3, "GitHub", detail, scores)  # duplicate = don't fix again
            _add("investigate", finding, -0.1, "GitHub", detail, scores)
        elif "no open issue" in finding.lower() or "novel" in finding.lower():
            _add("fix", finding, +0.15, "GitHub", detail, scores)
            _add("investigate", finding, +0.1, "GitHub", detail, scores)

    def _apply_tier_post(tier, detail, scores):
        if tier == "core":
            scores["remove"] -= 0.3
            scores["dismiss"] -= 0.3
            scores["fix"] += 0.1
        elif tier == "experimental":
            scores["fix"] -= 0.2
            scores["investigate"] -= 0.1

        # Consolidation candidate: cold infra surfaces are natural targets
        if tier == "infra" and days_cold > 7:
            scores["consolidate"] += 0.2
            scores["fix"] -= 0.05

        # Zero evidence: prefer passive dismissal over active investigation
        if fact_count == 0 and days_cold > 180:
            scores["dismiss"] += 0.2
            scores["investigate"] -= 0.1
            scores["fix"] -= 0.1

    ACTIONS = ["fix", "remove", "consolidate", "investigate", "dismiss", "escalate"]

    def _add(action: str, finding: str, weight: float, source: str, detail, scores):
        if abs(weight) < 0.01:
            return
        detail[action].append((finding, round(weight, 2), source))
        scores[action] += weight

    # ── Run scoring ───────────────────────────────────────────────

    scores, detail = _score_all()

    # Rank by net score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    recommendation = ranked[0][0]
    runner_up = ranked[1][0] if len(ranked) > 1 else None
    margin = round(ranked[0][1] - ranked[1][1], 2)

    # Decision confidence
    if margin >= 0.5:
        decision_confidence = "high"
    elif margin >= 0.2:
        decision_confidence = "medium"
    else:
        decision_confidence = "low"

    # ── Quality guardrails ──────────────────────────────────────

    # Store full ranked list before guardrails modify it
    ranked_full = [(a, detail[a], scores[a]) for a, _ in ranked]

    # Guardrail 1: Low confidence triggers information-seeking, not escalation.
    # The engine should gather more evidence until it can be decisive.
    if decision_confidence == "low" and not _retry:
        extra_checks = _seek_additional_evidence(signal_class, tier, name, checks,
                                                  live_state, days_cold, session_count)
        if extra_checks:
            all_checks = checks + extra_checks
            return _quantitative_decision(
                signal_class, tier, name, confidence, live_state,
                all_checks, days_cold, fact_count, session_count,
                _retry=True)
        # No extra evidence found. Information-seeking exhausted.
        # Fall through to standard guardrails — but flag that we tried.

    # Guardrail 2: When fix/investigate are negative and remove barely beats
    # dismiss, prefer dismiss (passive close) over remove (active deletion)...
    # UNLESS the surface has concrete traces that warrant cleanup.
    # Check if any positive-scoring check mentions "AGENTS.md" or "Docker" —
    # these indicate references or containers that should be removed.
    has_traces = any(
        "AGENTS.md" in t or "Docker" in t or "still referenced" in t.lower()
        for a in ("remove",)
        for t, w, _ in detail[a] if w > 0)
    if (recommendation == "remove"
            and scores.get("fix", 0) < 0
            and scores.get("investigate", 0) < 0
            and abs(scores.get("remove", 0) - scores.get("dismiss", 0)) < 0.15
            and not has_traces):
        recommendation = "dismiss"
        rationale = (
            f"Remove ({scores['remove']:+.1f}) barely beats dismiss "
            f"({scores['dismiss']:+.1f}), and fix/investigate are both "
            f"negative ({scores.get('fix',0):+.1f}/{scores.get('investigate',0):+.1f}). "
            f"No concrete references to clean up. DISMISS — close the issue "
            f"and let fresh signal re-surface if the problem persists."
        )

    # Guardrail 3: Engine dependency — the engine uses this surface itself.
    # If the engine is actively querying neo4j, parts-bin, doppler, or
    # memory.db, don't recommend removal. The tier classification may be
    # stale; self-referential validation catches it.
    if recommendation == "remove" and _is_engine_dependency(name):
        recommendation = "consolidate"
        runner_up = "remove"
        margin = 0.2  # override — it's an engine dependency
        rationale = (
            f"Engine dependency detected — this surface is actively used "
            f"by the audit pipeline itself. Reclassifying as INFRA. "
            f"Recommend CONSOLIDATE instead of REMOVE."
        )
        # Boost consolidate score for the rationale display
        scores["consolidate"] = scores.get("consolidate", 0) + 0.4

    # Guardrail 4: Core surface with duplicate issue → don't fix again.
    # An existing GitHub issue means someone is already on this. Fixing
    # again creates duplicate work. Dismiss or escalate.
    has_duplicate = any(
        "duplicate" in t.lower() or "open issue exists" in t.lower()
        for a in ("dismiss",)
        for t, w, _ in detail[a] if w > 0.3)
    if recommendation == "fix" and tier == "core" and has_duplicate:
        if scores.get("dismiss", 0) > -0.3:
            recommendation = "dismiss"
            rationale = (
                f"Core surface but an existing GitHub issue handles this. "
                f"DUPLICATE — dismiss this signal. The existing issue will "
                f"drive the fix. Creating a second issue creates confusion."
            )
        else:
            recommendation = "escalate"
            rationale = (
                f"Core surface with existing GitHub issue, but the duplicate "
                f"signal is weak. Operator should verify whether the existing "
                f"issue covers this specific problem."
            )

    # Build differential reasoning
    rec_detail = detail[recommendation]
    top_pro = max(rec_detail, key=lambda x: x[1]) if rec_detail else ("balanced", 0, "")
    top_con = min(rec_detail, key=lambda x: x[1]) if rec_detail else ("none", 0, "")

    rationale = (
        f"**{recommendation.upper()}** ({scores[recommendation]:+.1f}) "
        f"beats **{runner_up}** ({scores[runner_up]:+.1f}) by {margin:+.1f}. "
    )
    if margin >= 0.3:
        rationale += f"Decisive: \"{top_pro[0]}\" and similar findings outweigh alternatives."
    elif margin >= 0.1:
        rationale += f"Clear: \"{top_pro[0]}\" tips the balance."
    else:
        rationale += "Narrow: the top two actions are within noise range — review manually."

    return {
        "ranked": [(a, detail[a], scores[a]) for a, _ in ranked],
        "recommendation": recommendation,
        "runner_up": runner_up,
        "margin": margin,
        "rationale": rationale,
        "decision_confidence": decision_confidence,
        "scores": {a: round(s, 2) for a, s in scores.items()},
    }


def _format_quantitative_decision(qd: dict, name: str, signal_class: str,
                                   tier: str) -> str:
    """Format the quantitative decision as a detailed markdown section.

    Shows the recommendation with differential reasoning, then a table
    of how every action scored with specific check citations — not
    abstract categories.
    """
    lines = [
        "### Decision",
        "",
        f"**Recommendation: {qd['recommendation'].upper()}** "
        f"(margin: {qd['margin']:+.1f}, confidence: {qd['decision_confidence']})",
        "",
        f"Scores represent strength of case for each action. "
        f"Positive ≠ good surface — positive = strong argument for that action. "
        f"Negative = evidence opposes that action.",
        "",
        qd["rationale"],
        "",
        "### How each action scored",
        "",
        "Every check from the audit above scores each action. Higher = stronger case.",
        "",
        "| Action | Score | Driven by (top contributing checks) |",
        "|---|---|---|",
    ]

    for action, checks_list, score in qd["ranked"]:
        # Sort by absolute weight descending, take top 3
        top = sorted(checks_list, key=lambda x: abs(x[1]), reverse=True)[:3]
        drivers = "; ".join(
            f"{'[+]' if w > 0 else '[-]'} {t}" for t, w, _ in top
        ) if top else "—"
        marker = " [RECOMMENDED]" if action == qd["recommendation"] else ""
        lines.append(f"| **{action}**{marker} | **{score:+.2f}** | {drivers} |")

    return "\n".join(lines)


# ── Information-seeking ──────────────────────────────────────────

def _seek_additional_evidence(signal_class: str, tier: str, name: str,
                               checks: list[tuple], live_state: dict | None,
                               days_cold: int, session_count: int) -> list[tuple]:
    """Gather additional evidence when the engine can't decide.

    Tries in order of cost (cheapest first):
      1. Parts-bin — cached recycler decisions about this domain
      2. Deeper memory.db — full-session search for more context
      3. Additional live-state checks — if not already verified
      4. Frontier web search — for external context (if high-impact)

    Returns list of (source, finding, weight) tuples to add to checks.
    """
    extra = []

    # 1. Parts-bin: any cached recycler decisions about this domain?
    extra.extend(_check_parts_bin(name, signal_class))

    # 2. Deeper memory.db: full-session search for resolution patterns
    extra.extend(_deep_memory_search(name, signal_class))

    # 3. Additional live-state: if not checked, try a quick probe
    if not live_state or live_state.get("status") in ("unknown", "unchecked"):
        extra.extend(_quick_live_probe(name, tier, signal_class))

    return extra


def _check_parts_bin(name: str, signal_class: str) -> list[tuple]:
    """Search parts-bin for cached decisions about this domain."""
    try:
        result = subprocess.run(
            ["python", str(FACTORY / "scripts" / "parts-bin.py"),
             "search", name],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout[:500]
            weight = 0.1
            if signal_class == "pipeline-blocker":
                weight = 0.15
            return [("parts-bin", f"Cached decision found for '{name}': {output[:120]}", weight)]
    except Exception:
        pass
    return []


def _deep_memory_search(name: str, signal_class: str) -> list[tuple]:
    """Search memory.db for session context beyond basic fact counts."""
    extra = []
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)

        # Check for session summaries mentioning this domain
        row = db.execute(
            "SELECT COUNT(*) FROM facts WHERE category='session_summary' "
            "AND content LIKE ? AND created_at > datetime('now', '-30 days')",
            (f"%{name}%",)
        ).fetchone()
        if row and row[0] > 0:
            recent = row[0]
            if recent >= 5:
                extra.append(("memory.db", f"{recent} recent sessions mention '{name}' — actively relevant", 0.15))
            else:
                extra.append(("memory.db", f"{recent} recent sessions mention '{name}' — limited activity", 0.05))

        # Check for verification facts about this domain
        row = db.execute(
            "SELECT COUNT(*) FROM facts WHERE category='verification' "
            "AND content LIKE ? LIMIT 1",
            (f"%{name}%",)
        ).fetchone()
        if row and row[0] > 0:
            extra.append(("memory.db", f"Verification facts exist for '{name}' — past resolution attempted", 0.1))

        # Check for blocker resolution patterns
        row = db.execute(
            "SELECT content FROM facts WHERE category='blocker_narrative' "
            "AND content LIKE ? ORDER BY created_at DESC LIMIT 3",
            (f"%{name}%",)
        ).fetchall()
        if row:
            resolved = any("resolved" in r[0].lower() or "fixed" in r[0].lower()
                         or "working" in r[0].lower() for r in row)
            if resolved:
                extra.append(("memory.db", f"Previous resolution found for '{name}' — may be recurring", 0.1))

        db.close()
    except Exception:
        pass
    return extra


def _quick_live_probe(name: str, tier: str, signal_class: str) -> list[tuple]:
    """Attempt a quick live-state check for unverified surfaces."""
    extra = []
    if signal_class != "pipeline-blocker" or tier == "experimental":
        return extra

    # Common service ports mapped to quick HTTP checks
    port_map = {
        "hermes": "curl.exe -sI --connect-timeout 5 http://100.75.144.94:8150",
        "grafana": "curl.exe -sI --connect-timeout 5 http://100.75.144.94:3000",
        "n8n": "curl.exe -sI --connect-timeout 5 http://100.75.144.94:5678",
        "doppler": "doppler projects list --project motto-core --config prd",
    }
    if name not in port_map:
        return extra

    try:
        cmd = port_map[name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8, shell=True)
        if result.returncode == 0:
            extra.append(("live-state", f"Quick probe: '{name}' responded — is reachable", 0.15))
        elif result.returncode == 28:
            extra.append(("live-state", f"Quick probe: '{name}' timed out — may be down", -0.1))
        else:
            extra.append(("live-state", f"Quick probe: '{name}' responded with error code {result.returncode}", 0.05))
    except Exception:
        pass
    return extra


def _identify_information_gaps(signal_class: str, tier: str, name: str,
                                 checks: list[tuple], live_state: dict | None) -> str:
    """Identify what specific information would help resolve uncertainty."""
    gaps = []

    # Live-state gap
    if not live_state or live_state.get("status") in ("unknown", "unchecked"):
        gaps.append("live-state unverified — run a direct health check")

    # Memory freshness gap
    has_recent_memory = any("memory.db" in c[0] and "recent" in c[1].lower() for c in checks)
    if not has_recent_memory:
        gaps.append("no recent memory.db activity — session context may be stale")

    # GitHub dedup gap
    has_github = any("GitHub" in c[0] for c in checks)
    if not has_github:
        gaps.append("GitHub dedup not checked — may duplicate existing issue")

    # Surface documentation gap
    has_agents = any("AGENTS.md" in c[0] for c in checks)
    if not has_agents:
        gaps.append("AGENTS.md reference status unknown — may be undocumented")

    if not gaps:
        gaps.append("evidence is balanced despite full audit — operator should review")

    return "; ".join(gaps)


# ── Legacy compatibility wrappers ──────────────────────────────────

def _surface_pros_cons(name: str, tier: str, days_cold: int,
                        live_state: dict | None,
                        fact_count: int) -> dict:
    """Legacy wrapper — calls _quantitative_decision and maps to keep/remove."""
    # Build a minimal quantitative decision for backward compat
    confidence = ("medium", 0.5)  # placeholder
    checks = []
    if fact_count > 0:
        checks.append(("fact_count", f"{fact_count} historical facts", 0.1))
    qd = _quantitative_decision(
        signal_class="cold-capability", tier=tier, name=name,
        confidence=confidence, live_state=live_state, checks=checks,
        days_cold=days_cold, fact_count=fact_count)

    # Map from multi-action to pro/con format
    rec = qd["recommendation"]
    if rec == "fix" or rec == "consolidate":
        recommendation = "keep"
    elif rec == "remove":
        recommendation = "remove"
    elif rec == "dismiss":
        recommendation = "remove"  # dismiss of cold = remove
    else:
        recommendation = "audit-first"

    # Extract pro/con weights from the quantitative decision
    ranked = qd.get("ranked", [])
    pros: list = []
    cons: list = []
    pro_weight: float = 0.0
    con_weight: float = 0.0
    for action, checks_list, score in ranked:
        if action == "fix":
            pros = [(t, w) for t, w, _ in checks_list if w > 0]
            pro_weight = max(0.0, score)
        elif action == "remove":
            cons = [(t, -w) for t, w, _ in checks_list if w < 0]
            con_weight = max(0.0, abs(score)) if score < 0 else abs(score)

    return {
        "pros": [(a, w) for a, w in pros],
        "cons": [(a, -w) for a, w in cons],
        "recommendation": recommendation,
        "rationale": qd["rationale"],
        "pro_weight": round(max(0, pro_weight), 2),
        "con_weight": round(con_weight, 2),
    }


def _format_pros_cons(pc: dict) -> str:
    """Format a pro/con analysis as markdown (deprecated — use quantitative decision)."""
    lines = [
        "### Keep vs. Remove Analysis",
        "",
        f"**Recommendation: {pc['recommendation'].upper()}** — {pc['rationale']}",
        "",
        "| | Weight | Arguments |",
        "|---|---|",
    ]
    for arg, weight in pc.get("pros", []):
        lines.append(f"| KEEP | +{weight:.1f} | {arg} |")
    for arg, weight in pc.get("cons", []):
        lines.append(f"| REMOVE | {weight:.1f} | {arg} |")
    lines.append("| | | |")
    lines.append(f"| **Net** | **{pc.get('pro_weight', 0) - pc.get('con_weight', 0):+.1f}** | "
                 f"Keep: {pc.get('pro_weight', 0):.1f} / Remove: {pc.get('con_weight', 0):.1f} |")
    return "\n".join(lines)


def _build_decision(signal_class: str, tier: str, confidence: tuple[str, float],
                    pros_cons: dict | None, live_state: dict | None,
                    checks: list[tuple], payload: dict) -> str:
    """Build a reasoned decision section driven by quantitative analysis.

    The primary output is a quantitative decision: every possible action
    (fix, remove, consolidate, investigate, dismiss, escalate) scored
    on the same weighted criteria, producing comparable net scores.
    The recommendation falls out of the numbers — not hand-authored.

    Priority is a secondary footnote for triage ordering.
    """
    level, score = confidence
    days_cold = payload.get("days_cold", 0)
    domain = payload.get("domain", payload.get("probe", payload.get("name", "unknown")))
    session_count = payload.get("session_count", 0)
    fact_count = payload.get("fact_count", 0)

    # Primary: quantitative decision engine
    qd = _quantitative_decision(
        signal_class=signal_class, tier=tier, name=domain,
        confidence=confidence, live_state=live_state, checks=checks,
        days_cold=days_cold, fact_count=fact_count,
        session_count=session_count)

    qd_table = _format_quantitative_decision(qd, domain, signal_class, tier)

    # Secondary: priority (urgency for triage)
    action, action_label, reasoning = _decide_action(
        signal_class, tier, level, score, pros_cons, live_state, checks, payload)

    lines = [
        qd_table,
        "",
        "---",
        "",
        "### Priority (triage)",
        "",
        f"**{action_label}**",
        "",
        reasoning,
        "",
        "#### Signal summary",
        "",
        f"| Factor | Value |",
        f"|---|---|",
        f"| Signal class | {signal_class} |",
        f"| Surface | {domain} |",
        f"| Tier | {tier.upper()} |",
        f"| Confidence | {level.upper()} ({score:.0%}) |",
    ]

    if days_cold > 0:
        lines.append(f"| Days cold | {days_cold}d |")
    if session_count > 0:
        lines.append(f"| Sessions affected | {session_count} |")

    ls_status = live_state.get("status", "unchecked") if live_state else "unchecked"
    lines.append(f"| Live state | {ls_status} |")

    if pros_cons:
        lines.append(f"| Pro/con net | {pros_cons['recommendation'].upper()} "
                      f"({pros_cons['pro_weight'] - pros_cons['con_weight']:+.1f}) |")

    lines.append("")
    lines.append("#### How this decision was reached")
    lines.append("")
    lines.append("1. **Tier check**: " + _tier_reasoning(tier))
    lines.append("2. **Confidence check**: " + _confidence_reasoning(level, checks))
    lines.append("3. **Live-state check**: " + _livestate_reasoning(live_state))
    lines.append("4. **Surface audit**: " + _surface_audit_reasoning(pros_cons, tier, days_cold))
    lines.append("5. **Minimalist principle**: " + _minimalist_reasoning(tier, level, action))

    return "\n".join(lines)


def _decide_action(signal_class: str, tier: str, level: str, score: float,
                   pros_cons: dict | None, live_state: dict | None,
                   checks: list[tuple], payload: dict) -> tuple[str, str, str]:
    """Apply the decision matrix to produce action + label + reasoning.

    Decision framework (frontier-derived, 2026-07-18):
      Adapted from three production patterns:
      1. PagerDuty SEV-1..SEV-5: severity levels with defined impact, scope,
         and expected response. "Always assume the worst" — escalate if unsure.
      2. RICE/ICE: Reach × Impact × Confidence ÷ Effort. Score comparably
         across items so you can rank what matters most.
      3. Issue AI Agent (alexyan0431): structured JSON classification validated
         against a whitelist, two-stage dedup (search API then LLM), stateless
         per-step failure tolerance.

    Our priority levels (adapted from PagerDuty SEV model):
      PRI-1 (Critical): Core surface down or producing bad output. Revenue at
        risk. Fix immediately, no deferral.
      PRI-2 (High): Infra surface confirmed failing with high confidence.
        Degrades operational visibility. Fix within session.
      PRI-3 (Medium): Surface needs investigation or consolidation. Evidence
        is plausible but not overwhelming. Audit-first approach.
      PRI-4 (Low): Experimental/dead surface. Decommission or dismiss. Do not
        invest cycles in abandoned experiments.
      PRI-5 (Cosmetic): Stale or contradictory signal. Close. The system will
        re-detect genuine problems.
    """
    ls_status = live_state.get("status", "unknown") if live_state else "unknown"

    # Calculate impact score (RICE-derived)
    impact = _compute_impact(signal_class, tier, ls_status)

    # ── Decision matrix (ordered by priority) ────────────────────────

    # PRI-1: Core surface with active problem → CRITICAL
    if tier == "core" and ls_status in ("alive", "running", "active"):
        if level in ("high", "medium"):
            return (
                "APPLY",
                "PRI-1 CRITICAL — Apply fix immediately",
                _critical_reasoning(signal_class, tier, ls_status, level)
            )
        if ls_status in ("dead", "not_found", "unreachable"):
            return (
                "APPLY",
                "PRI-1 CRITICAL — Restore then fix",
                (f"This is a **core** surface ({signal_class}) that is DOWN or unreachable "
                 f"({ls_status}). A core surface offline is itself the emergency. "
                 f"Restore connectivity first, then verify the underlying issue. "
                 f"If the surface was intentionally decommissioned, escalate immediately.")
            )

    # PRI-2: Infra surface confirmed failing → HIGH
    if tier == "infra" and level == "high" and ls_status in ("alive", "running"):
        return (
            "APPLY",
            "PRI-2 HIGH — Fix confirmed infra problem",
            (f"**Infra** surface ({signal_class}) is ALIVE and confirmed failing "
             f"with {level} confidence. Multiple sources agree. While infra isn't "
             f"directly revenue-critical, its failure degrades operational visibility "
             f"across the fleet. Apply the fix, verify, confirm healthy state.")
        )

    # PRI-3: Plausible but uncertain → INVESTIGATE
    if level in ("medium", "low") and tier != "experimental":
        if pros_cons and pros_cons.get("recommendation") == "remove":
            return (
                "DECOMMISSION",
                "PRI-4 LOW — Surface tilted toward removal",
                (f"This {tier}-tier surface has a pro/con analysis tilting toward removal. "
                 f"Before decommissioning, verify no other surface depends on it. "
                 f"If standalone, remove to reduce operational surface area.")
            )
        return (
            "INVESTIGATE",
            "PRI-3 MEDIUM — Investigate before acting",
            (f"The signal is **{level}** confidence on a {tier}-tier surface. Evidence "
             f"is plausible but not overwhelming. Before applying any fix: "
             f"(1) verify live state manually, (2) check source facts still current, "
             f"(3) search for pre-existing fixes in recent sessions. Reclassify or "
             f"dismiss after investigation.")
        )

    # PRI-4: Experimental surface → DECOMMISSION or DISMISS
    if tier == "experimental":
        if level in ("high", "medium"):
            return (
                "DECOMMISSION",
                "PRI-4 LOW — Decommission abandoned experiment",
                _experimental_reasoning(signal_class, level)
            )
        else:
            return (
                "DISMISS",
                "PRI-5 COSMETIC — Dismiss stale experimental signal",
                (f"**Experimental** surface with {level} confidence. The evidence is "
                 f"weak — likely stale memory.db facts from testing. Close this issue. "
                 f"If the surface reappears in active sessions, it will be re-evaluated.")
            )

    # PRI-5: Stale signal → DISMISS
    if level == "stale":
        return (
            "DISMISS",
            "PRI-5 COSMETIC — Dismiss stale signal",
            (f"The signal is **stale** — evidence is contradictory, facts are old, "
             f"or the source was fixed since generation. Per the Minimalist Operations "
             f"Principle, do not act on weak evidence. Close this issue. A fresh signal "
             f"will be generated if the problem persists.")
        )

    # Fallthrough: balanced trade-offs → HUMAN
    return (
        "HUMAN_DECISION",
        "PRI-3 HUMAN — Operator judgment required",
        (f"The evidence does not clearly point to a single action ({tier}-tier, "
         f"{level} confidence, live-state: {ls_status}). Review the audit trail and "
         f"pro/con analysis above. Per the Minimalist Operations Principle, when in "
         f"doubt, bias toward subtraction — but the decision requires operator judgment.")
    )


def _compute_impact(signal_class: str, tier: str, ls_status: str) -> float:
    """Compute impact score (0-1) using RICE-derived factors."""
    base = 0.0
    if tier == "core":
        base = 0.9
    elif tier == "infra":
        base = 0.5
    elif tier == "experimental":
        base = 0.1

    # Signal class modifier
    if signal_class == "behavior-fix":
        base *= 0.7  # Behavior fixes affect future sessions, not current operations
    elif signal_class == "pipeline-blocker":
        base *= 1.0  # Pipeline blockers directly affect current work
    elif signal_class == "cold-capability":
        base *= 0.4  # Cold surfaces are about potential, not active problems

    # Live-state modifier
    if ls_status in ("alive", "running", "active"):
        base *= 1.0  # Running: problem is active
    elif ls_status in ("dead", "not_found"):
        base *= 0.3  # Dead: problem is moot unless surface should be alive
    elif ls_status == "unreachable":
        base *= 0.5  # Can't verify
    return round(min(1.0, base), 2)


def _critical_reasoning(signal_class: str, tier: str, ls_status: str, level: str) -> str:
    return (
        f"This is a **{tier}** surface ({signal_class}) that is **{ls_status.upper()}** "
        f"but failing. The signal is **{level}** confidence with corroborating evidence "
        f"from memory.db, live-state verification, and AGENTS.md. "
        f"{'Revenue-critical' if tier == 'core' else 'Operationally critical'} "
        f"surface — failure here has direct business impact. "
        f"**Apply the suggested fix**, verify with the listed verification "
        f"command, and confirm resolution within the same session. "
        f"Do not defer — this is the highest priority class."
    )


def _experimental_reasoning(signal_class: str, level: str) -> str:
    return (
        f"This is an **experimental** surface ({signal_class}) that was tested but "
        f"did not become part of the operational workflow. The signal is "
        f"**{level}** confidence — meaning multiple sources confirm it's inactive "
        f"or broken. Per the Minimalist Operations Principle, experimental "
        f"surfaces should be **removed, not fixed**. Every surface costs "
        f"attention overhead. Archive all references in AGENTS.md, remove "
        f"Docker containers or services, and close any related issues. "
        f"If this capability is genuinely needed, it should be rebuilt on a "
        f"proven foundation, not revived from abandoned experiments."
    )


def _tier_reasoning(tier: str) -> str:
    return {
        "core": "This surface is revenue-critical. Failure has direct business impact.",
        "infra": "This surface provides operational visibility. Failure degrades situational awareness.",
        "experimental": "This surface was tested and abandoned. It should not be improved — it should be removed.",
    }.get(tier, "This surface has no assigned tier — needs classification.")


def _confidence_reasoning(level: str, checks: list[tuple]) -> str:
    pos = sum(1 for _, _, w in checks if w > 0)
    neg = sum(1 for _, _, w in checks if w < 0)
    detail = f"{pos} corroborating checks, {neg} contradicting checks."
    if level == "high":
        return f"Evidence is strong and consistent. {detail} Multiple independent sources agree."
    elif level == "medium":
        return f"Evidence is plausible but not certain. {detail} Verify key assumptions."
    elif level == "low":
        return f"Evidence is weak or mixed. {detail} Do not act without further investigation."
    else:
        return f"Evidence is stale or contradictory. {detail} Likely noise from testing or fixed issues."


def _livestate_reasoning(live_state: dict | None) -> str:
    if not live_state:
        return "Live-state was not checked. Assume the surface may be in any state."
    status = live_state.get("status", "unknown")
    detail = live_state.get("detail", "")
    if status == "alive":
        return f"Surface is confirmed ALIVE ({detail}). The problem is real, not a detection artifact."
    elif status in ("dead", "not_found"):
        return f"Surface is confirmed DOWN ({detail}). May be intentionally stopped — check before acting."
    elif status == "unreachable":
        return f"Surface could not be reached ({detail}). Network or Docker may be the cause, not the surface."
    return f"Live-state is {status}. Manual verification recommended."


def _surface_audit_reasoning(pros_cons: dict | None, tier: str, days_cold: int) -> str:
    if not pros_cons:
        return "No pro/con analysis available for this surface class."
    rec = pros_cons.get("recommendation", "unknown")
    if rec == "remove":
        return (f"Pro/con analysis recommends REMOVAL ({pros_cons['con_weight']:.1f} vs "
                f"{pros_cons['pro_weight']:.1f} keep). Arguments for removal outweigh preservation.")
    elif rec == "keep":
        return (f"Pro/con analysis recommends PRESERVATION ({pros_cons['pro_weight']:.1f} vs "
                f"{pros_cons['con_weight']:.1f} remove). Surface serves a current use case.")
    else:
        return (f"Pro/con analysis is balanced ({pros_cons['pro_weight']:.1f} keep vs "
                f"{pros_cons['con_weight']:.1f} remove). Manual review needed.")


def _minimalist_reasoning(tier: str, level: str, action: str) -> str:
    if action == "DECOMMISSION":
        return ("Removing this surface reduces operational surface area. Every removed "
                "surface is one less thing to monitor, debug, and maintain.")
    if action == "DISMISS":
        return ("Dismissing weak signals prevents noise from consuming attention. The "
                "system will re-detect genuine problems in future sessions.")
    if action == "APPLY":
        return ("This surface justifies its existence. Fixing it directly serves the "
                "revenue or operational goal it supports.")
    return ("When evidence is balanced, operator judgment is the tiebreaker. The system "
            "provides context; the operator decides.")

def _read_agents_md() -> str:
    if AGENTS_MD.exists():
        return AGENTS_MD.read_text(encoding="utf-8").lower()
    return ""


def _memory_has_recent_pass(probe: str) -> bool:
    """Check if a behavior probe has PASSed in recent memory."""
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)
        row = db.execute(
            "SELECT COUNT(*) FROM facts WHERE category='behavior_test' "
            "AND content LIKE ? AND content LIKE '%verdict=pass%' "
            "AND created_at > datetime('now', '-14 days')",
            (f"%{probe}%",)
        ).fetchone()
        db.close()
        return row and row[0] > 0
    except Exception:
        return False


def _memory_fact_age(category: str, keyword: str) -> int | None:
    """Get age in days of the newest fact matching category + keyword."""
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)
        row = db.execute(
            "SELECT MAX(created_at) FROM facts WHERE category=? AND content LIKE ?",
            (category, f"%{keyword}%")
        ).fetchone()
        db.close()
        if row and row[0]:
            fact_dt = datetime.fromisoformat(row[0])
            return (datetime.now() - fact_dt).days
        return None
    except Exception:
        return None


def _memory_fact_count(category: str, keyword: str) -> int:
    """Count facts in a category matching a keyword."""
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)
        row = db.execute(
            "SELECT COUNT(*) FROM facts WHERE category=? AND content LIKE ?",
            (category, f"%{keyword}%")
        ).fetchone()
        db.close()
        return row[0] if row else 0
    except Exception:
        return 0


def _memory_has_recent_fact(category: str, keyword: str, days: int = 7) -> bool:
    """Check if a fact exists in memory within the last N days."""
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)
        row = db.execute(
            "SELECT COUNT(*) FROM facts WHERE category=? AND content LIKE ? "
            "AND created_at > datetime('now', ?)",
            (category, f"%{keyword}%", f"-{days} days")
        ).fetchone()
        db.close()
        return row and row[0] > 0
    except Exception:
        return False


def _memory_recurring_timestamps(domain: str) -> tuple[str | None, str | None]:
    """Get first_seen and last_seen from recurring_error metadata."""
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)
        row = db.execute(
            "SELECT metadata FROM facts WHERE category='recurring_error' "
            "AND content LIKE ? LIMIT 1",
            (f"%{domain}%",)
        ).fetchone()
        db.close()
        if row and row[0]:
            meta = json.loads(row[0])
            return meta.get("last_seen"), meta.get("first_seen")
    except Exception:
        pass
    return None, None


def _memory_total_sessions() -> int:
    """Get approximate total session count."""
    try:
        db = sqlite3.connect(f"file:{MEMORY_DB}?mode=ro", uri=True)
        row = db.execute(
            "SELECT COUNT(DISTINCT metadata) FROM facts WHERE category='session_summary'"
        ).fetchone()
        db.close()
        return row[0] if row else 0
    except Exception:
        return 0


def _github_has_open_issue(keyword: str, signal_class: str) -> bool | None:
    """Check GitHub for open issues matching keyword + class. Returns None if can't check."""
    try:
        token_result = subprocess.run(
            ["doppler", "secrets", "get", "GITHUB_PAT", "--plain",
             "-p", "auth-sso", "-c", "prd"],
            capture_output=True, text=True, timeout=10,
        )
        if token_result.returncode != 0 or len(token_result.stdout.strip()) < 5:
            return None

        result = subprocess.run(
            ["gh", "issue", "list", "--repo", "lkmotto/fleet-triage",
             "--state", "open", "--search", keyword, "--json", "number,title",
             "--limit", "5"],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "GH_TOKEN": token_result.stdout.strip()},
        )
        if result.returncode != 0:
            return None

        issues = json.loads(result.stdout)
        for issue in issues:
            title_lower = issue.get("title", "").lower()
            if keyword.lower() in title_lower and signal_class.lower() in title_lower:
                return True
        return False
    except Exception:
        return None


def _check_docker_on_ms01() -> str | None:
    """Check Docker status on ms01. Returns 'up', 'down', or None."""
    try:
        # Use ms01admin key auth via Tailscale
        result = subprocess.run(
            ["ssh", "-i", str(FACTORY.parent / ".ssh" / "legion_ms01_v2"),
             "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new",
             "-o", "BatchMode=yes", "ms01admin@100.75.144.94",
             "docker", "ps", "2>&1"],
            capture_output=True, text=True, timeout=12,
        )
        if result.returncode == 0 and "CONTAINER" in result.stdout:
            return "up"
        return "down"
    except subprocess.TimeoutExpired:
        return "down"
    except Exception:
        return None


def _compute_confidence(corroboration: float, total_weight: float) -> tuple[str, float]:
    """Compute confidence level from weighted checks."""
    if total_weight == 0:
        return "low", 0.3
    # Normalize to 0-1 range, then clamp
    normalized = max(0.0, min(1.0, (corroboration / total_weight + 0.5)))
    if normalized >= 0.8:
        return "high", normalized
    elif normalized >= 0.5:
        return "medium", normalized
    elif normalized >= 0.3:
        return "low", normalized
    else:
        return "stale", normalized


def _build_audit_report(confidence: tuple[str, float], checks: list[tuple],
                        pros_cons: dict | None = None,
                        decision: str | None = None) -> dict:
    """Build the audit report dict."""
    level, score = confidence
    narrative_lines = [
        f"### Audit Trail",
        f"",
        f"**Confidence: {level.upper()} ({score:.0%})** — {_confidence_explanation(level)}",
        f"",
    ]

    pos_checks = [(src, f, w) for src, f, w in checks if w > 0]
    neg_checks = [(src, f, w) for src, f, w in checks if w < 0]
    neu_checks = [(src, f, w) for src, f, w in checks if w == 0]

    if pos_checks:
        narrative_lines.append("**Corroborating (+):**")
        for src, finding, _ in pos_checks:
            narrative_lines.append(f"- [{src}] {finding}")
        narrative_lines.append("")

    if neg_checks:
        narrative_lines.append("**Contradicting (-):**")
        for src, finding, _ in neg_checks:
            narrative_lines.append(f"- [{src}] {finding}")
        narrative_lines.append("")

    if neu_checks:
        narrative_lines.append("**Neutral:**")
        for src, finding, _ in neu_checks:
            narrative_lines.append(f"- [{src}] {finding}")
        narrative_lines.append("")

    # Append pro/con analysis if available
    if pros_cons:
        narrative_lines.append("")
        narrative_lines.append(_format_pros_cons(pros_cons))

    # Append decision section
    if decision:
        narrative_lines.append("")
        narrative_lines.append(decision)

    return {
        "confidence": level,
        "confidence_score": score,
        "narrative": "\n".join(narrative_lines),
        "checks": [{"source": s, "finding": f, "weight": w} for s, f, w in checks],
        "audited_at": datetime.now().isoformat(),
        "pros_cons": pros_cons,
    }


def _confidence_explanation(level: str) -> str:
    return {
        "high": "Multiple sources agree. Signal is fresh and corroborated. Act with confidence.",
        "medium": "Signal is plausible but limited corroboration. Verify key assumptions before acting.",
        "low": "Weak or conflicting evidence. Investigate further before applying any fix.",
        "stale": "Signal is likely stale or contradicted. Close or requeue for manual review.",
    }.get(level, "Unknown")


def _empty_audit(reason: str) -> dict:
    return {
        "confidence": "low",
        "confidence_score": 0.3,
        "narrative": f"### Audit Trail\n\n**No audit performed:** {reason}\n",
        "checks": [],
        "audited_at": datetime.now().isoformat(),
    }


def build_audit_section(audit: dict) -> str:
    """Extract the markdown narrative for appending to an issue body."""
    return audit.get("narrative", "")


# ── Standalone CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep-audit a review-queue item")
    parser.add_argument("item_id", help="Review queue item ID")
    parser.add_argument("--json", action="store_true", help="Output full audit JSON")
    args = parser.parse_args()

    rq_path = FACTORY / "knowledge" / "review-queue.json"
    if not rq_path.exists():
        print(json.dumps({"error": "review-queue.json not found"}))
        return

    items = json.loads(rq_path.read_text())
    item = next((i for i in items if i["id"] == args.item_id), None)
    if not item:
        print(json.dumps({"error": f"Item {args.item_id} not found"}))
        return

    audit = audit_item(item)
    if args.json:
        print(json.dumps(audit, indent=2, ensure_ascii=False))
    else:
        print(audit["narrative"])
        print(f"\nConfidence: {audit['confidence'].upper()} ({audit['confidence_score']:.0%})")


if __name__ == "__main__":
    main()
