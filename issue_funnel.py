"""
Full-spectrum issue funnel: reads ALL fact types from memory.db, extracts micro-patterns,
cross-references domains across dimensions, feeds deep_audit with rich signal, and produces
ranked issues with quantitative remediation payoff scoring.

Architecture:
  1. SignalCollector — reads all 29 fact types, groups by domain
  2. GoalInference — derives production goals from AGENTS.md + memory patterns
  3. SubPatternExtractor — within each domain, extracts distinct error/issue types
  4. CrossReferencer — correlates signals across fact types per domain
  5. DecisionFeeder — packages rich signal for deep_audit
  6. PayoffScorer — quantitative remediation ROI: (Impact × Confidence) / Cost
  7. MemoryCollaborator — deep context from full-session-search + harvester
"""
import sqlite3, json, sys, re, os, subprocess
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

FACTORY = Path.home() / ".factory"
DB_PATH = FACTORY / "memory.db"
sys.path.insert(0, str(FACTORY / "scripts"))
from deep_audit import audit_item, SURFACE_TIERS, _is_engine_dependency, _memory_recurring_timestamps
from scanners import GitHubScanner, Neo4jScanner, OTELScanner

# ═══════════════════════════════════════════════════════════════════
# 1. SIGNAL COLLECTOR — read ALL fact types from memory.db
# ═══════════════════════════════════════════════════════════════════

class SignalCollector:
    """Ingest all live facts from memory.db and organize by domain + type."""

    # Domains we track (from SURFACE_TIERS + known topics)
    # Exclude noise domains: "factory" and "mcp" match system references, not errors
    TRACKED_DOMAINS = set(SURFACE_TIERS.keys()) | {
        "ntreis", "truetracts", "taxnet", "ssh", "wsl", "ollama",
        "steel", "playwright", "comet", "powershell",
        "perplexity", "tavily", "github", "git", "hostinger",
        "supabase", "deepseek", "resend", "neon", "sqlite",
        "permission", "timeout", "path", "credential",
        "sdr-agent", "appraisal", "bidding", "order-monitor",
        "credential-grabber", "sfrep", "openhands", "sharepoint",
        "workfile", "email-loe", "fleet-triage",
    }

    # Noise domains: match on too many generic references, not real errors
    NOISE_DOMAINS = {"factory", "mcp", "skill"}

    # Domain aliases: domains that overlap and should be collapsed
    DOMAIN_ALIASES = {
        "appraisal": "appraisal-pipeline",  # "appraisal" matches "appraisal-pipeline" facts
    }

    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(str(db_path))
        self.domains: dict[str, dict] = defaultdict(lambda: defaultdict(list))
        self.raw_facts: dict[str, list] = defaultdict(list)
        self.fact_counts: dict[str, int] = defaultdict(int)

    def collect(self):
        """Read all live facts and index by domain + fact type."""
        rows = self.db.execute(
            "SELECT category, content, created_at, metadata FROM facts WHERE status='live'"
        ).fetchall()

        for cat, content, created_at, meta in rows:
            self.raw_facts[cat].append((content, created_at, meta))
            self.fact_counts[cat] += 1

            # Determine which domain(s) this fact belongs to
            cl = content.lower()
            matched = set()
            for d in self.TRACKED_DOMAINS:
                d_clean = d.lower().replace("-", "").replace("_", "")
                if d_clean in cl.replace("-", "").replace("_", ""):
                    matched.add(d)

            if not matched:
                continue  # no tracked domain

            for d in matched:
                if d in self.NOISE_DOMAINS:
                    continue
                # Collapse aliases
                d = self.DOMAIN_ALIASES.get(d, d)
                self.domains[d][cat].append({
                    "content": content[:500],
                    "created_at": created_at,
                    "meta": meta,
                })

        self.db.close()
        return self

    def get_domain_signal(self, domain: str) -> dict:
        """Get all signal for a domain organized by fact type."""
        return dict(self.domains.get(domain, {}))


# ═══════════════════════════════════════════════════════════════════
# 2. SUB-PATTERN EXTRACTOR — micro-issues within each domain
# ═══════════════════════════════════════════════════════════════════

class SubPatternExtractor:
    """Extract distinct error/issue types within a domain from source facts.

    Priority order:
      1. 'error' facts — specific error messages (most reliable)
      2. 'recurring_error' samples — aggregated error types across sessions
      3. 'blocker_narrative' — full causal chain: intent → error → impact → outcome

    For blocker narratives, we extract the COMPLETE causal chain, not just
    the error sentence. This produces issues with: what was tried, what broke,
    what was impacted, what was attempted to fix it, and whether it worked.
    """

    ERROR_INDICATORS = [
        r'fail(?:ed|ing|s)?\b', r'error\b', r'broken\b', r"can'?t\b",
        r'unable\b', r'timeout\b', r'40[13]\b', r'50[0-9]\b',
        r'\bdown\b', r'offline\b', r'blocked\b', r'denied\b',
        r'not (?:working|responding|reachable|available|found|installed)',
        r'missing\b', r'expired\b', r'invalid\b', r'crashed\b',
        r'refused\b', r'unreachable\b', r'hung\b', r'stuck\b',
    ]

    NOISE_SENTENCES = [
        r'^here.{0,10}(is|are|was|were)\s', r'^let me\s', r'^yes[,.]?\s',
        r'^done[.!]?\s*$', r'^good\s', r'^ok[,.]?\s', r'^all\s',
        r'^both\s', r'^everything\s', r'^this\s',
        r'^you.{0,5}(are|were)\s', r'^i\s', r'^the\s',
        r'^#+\s', r'^\*\*', r'^<json-render>', r'^```',
        r'^\d+\)\s', r'^-{3,}', r'^review complete',
    ]

    @staticmethod
    def extract(domain: str, domain_signal: dict) -> list[tuple[str, int]]:
        patterns = Counter()

        # Priority 1: 'error' facts — wrap in causal chain format
        for fact in domain_signal.get("error", []):
            content = fact["content"]
            m = re.search(r'error:?\s*(.{10,200})', content)
            if m:
                err = m.group(1).strip()
                if len(err) > 15 and SubPatternExtractor._has_error_indicator(err):
                    patterns[f"error: {err[:120]}"] += 1

        # Priority 2: 'recurring_error' samples
        for fact in domain_signal.get("recurring_error", []):
            content = fact["content"]
            m = re.search(r'samples:\s*(.{20,300})', content)
            if m:
                sample = m.group(1)
                for part in re.split(r'\s*\|\s*', sample):
                    part = re.sub(r'^error:?\s*', '', part.strip())
                    if len(part) > 15 and SubPatternExtractor._has_error_indicator(part):
                        patterns[f"error: {part[:120]}"] += 1

        # Priority 3: 'blocker_narrative' — full causal chain
        for fact in domain_signal.get("blocker_narrative", []):
            content = fact["content"]
            m = re.search(r'\[BLOCKER\s+from\s+\w+\]\s*(.*)', content, re.DOTALL)
            if m:
                causal = SubPatternExtractor._extract_causal_chain(m.group(1))
                if causal:
                    patterns[causal] += 1

        return patterns.most_common(5)

    @staticmethod
    def _extract_causal_chain(text: str) -> str | None:
        """Extract causal chain: intent -> error -> impact -> [outcome].

        Detects 5 blocker narrative formats and parses each differently:
          1. sections: "Here's where things stand" + "What worked"/"What failed"
          2. numbered: "The pipeline ran. 1. ... 4. Failed at..."
          3. blocker-list: "I've hit two blockers. 1. No SSH key..."
          4. headers: "## Status" or "## Sitrep" with bullet points
          5. plain: single error sentence
        """
        text = re.sub(r'<json-render>.*?</json-render>', ' ', text, flags=re.DOTALL)
        text = re.sub(r'```.*?```', ' ', text, flags=re.DOTALL)
        text = re.sub(r'#{1,4}\s+', '', text)
        text = re.sub(r'\*\*', '', text)  # strip bold markers

        # Detect format
        has_sections = bool(re.search(r'(?:what\s+(?:worked|failed|succeeded)|root cause)', text.lower()))
        has_numbered = bool(re.search(r'^\d+[\.\)]\s', text, re.MULTILINE))
        has_blocker_list = bool(re.search(r"(?:i'?ve\s+(?:hit|found|got)|here(?:'s| are| were)\s+(?:two|three|\d+)\s+block)", text.lower()))

        # Dispatch to format-specific parser
        if has_sections:
            return SubPatternExtractor._parse_sections(text)
        elif has_blocker_list:
            return SubPatternExtractor._parse_blocker_list(text)
        elif has_numbered:
            return SubPatternExtractor._parse_numbered(text)
        else:
            return SubPatternExtractor._parse_plain(text)

    @staticmethod
    def _parse_sections(text: str) -> str | None:
        """Parse sections format: 'What failed' / 'What worked' / 'Blocker:'"""
        intent = None
        error = None
        impacts = []
        remediation = None
        outcome = None

        # Intent: first line before any section
        first_line = text.split('\n')[0].strip().rstrip(':')
        if first_line and len(first_line) > 5:
            intent = first_line[:80]

        # Find errors under "What failed" or "Blocker:" markers
        failed_section = re.search(r'(?:what\s+failed|blocker)[:\s]*(.*?)(?:what\s+worked|$)', text, re.IGNORECASE | re.DOTALL)
        if failed_section:
            failed_text = failed_section.group(1)
            # Extract bullet points or sentences
            for line in re.split(r'[\n-]\s*', failed_text):
                line = line.strip()
                if len(line) > 10 and SubPatternExtractor._has_error_indicator(line):
                    if not error:
                        error = line[:120]
                    else:
                        impacts.append(line[:100])

        # If no "What failed" section, search for "Blocker:" lines
        if not error:
            for line in text.split('\n'):
                if re.search(r'blocker[:\s]', line.lower()) and SubPatternExtractor._has_error_indicator(line):
                    parts = re.split(r'blocker[:\s]+', line, maxsplit=1, flags=re.IGNORECASE)
                    if len(parts) > 1 and len(parts[1].strip()) > 10:
                        error = parts[1].strip()[:120]
                        break

        # Remediation from "What worked"
        worked_section = re.search(r'what\s+worked[:\s]*(.*?)(?:what\s+failed|$)', text, re.IGNORECASE | re.DOTALL)
        if worked_section:
            worked_text = worked_section.group(1)
            first = worked_text.strip().split('\n')[0].strip('- ').strip()
            if len(first) > 10:
                remediation = first[:120]

        # Outcome
        outcome = SubPatternExtractor._detect_outcome(text)

        if not error:
            return None

        return SubPatternExtractor._build_chain(intent, error, impacts, remediation, outcome)

    @staticmethod
    def _parse_blocker_list(text: str) -> str | None:
        """Parse 'I've hit N blockers' format."""
        intent = None
        errors = []
        impacts = []

        # Intent from first sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences[:3]:
            s = s.strip()
            if s and not SubPatternExtractor._has_error_indicator(s) and len(s) > 10:
                intent = s[:80]
                break

        # Each numbered blocker is an error + impact pair
        blockers = re.split(r'\*\*\d+[\.\)]\s*\*\*|\d+[\.\)]\s*\*', text)
        for block in blockers[1:]:  # skip text before first blocker
            block = block.strip()
            if len(block) < 10:
                continue
            # First sentence = error, rest = impact
            bs = re.split(r'(?<=[.!?])\s+', block)
            if bs and len(bs[0]) > 10:
                if SubPatternExtractor._has_error_indicator(bs[0]):
                    errors.append(bs[0][:120])
                    if len(bs) > 1 and len(bs[1]) > 10:
                        impacts.append(bs[1][:100])

        if not errors:
            return None

        outcome = SubPatternExtractor._detect_outcome(text)
        return SubPatternExtractor._build_chain(
            intent,
            "; ".join(errors[:2]),
            impacts[:2],
            None,
            outcome
        )

    @staticmethod
    def _parse_numbered(text: str) -> str | None:
        """Parse numbered list format: 'The pipeline ran. 1. ... 4. Failed at...'"""
        intent = None
        error = None
        impacts = []

        sentences = re.split(r'(?<=[.!?])\s+', text, maxsplit=2)
        if sentences and len(sentences[0]) > 10:
            intent = sentences[0].strip()[:80]

        # Find the numbered item containing the failure
        for item in re.split(r'\n?\d+[\.\)]\s+', text):
            item = item.strip()
            if SubPatternExtractor._has_error_indicator(item):
                # Split into what was tried (before the error) and the error
                parts = re.split(r'(?<=[.!?])\s+', item, maxsplit=1)
                if len(parts) > 1:
                    error = parts[-1][:120]
                else:
                    error = item[:120]
                break

        if not error:
            return None

        outcome = SubPatternExtractor._detect_outcome(text)
        return SubPatternExtractor._build_chain(intent, error, impacts, None, outcome)

    @staticmethod
    def _parse_plain(text: str) -> str | None:
        """Parse plain text: find the error sentence and surrounding context."""
        intent = None
        error = None
        impacts = []

        sentences = re.split(r'(?<=[.!?])\s+', text)

        for i, s in enumerate(sentences):
            s = s.strip()
            if len(s) < 10:
                continue
            if SubPatternExtractor._is_narrative_noise(s):
                continue

            # Intent: first non-noise, non-error sentence
            if intent is None and not SubPatternExtractor._has_error_indicator(s):
                intent = s[:80]

            # Error: first error-indicating sentence
            if error is None and SubPatternExtractor._has_error_indicator(s):
                error = s[:120]
                # Impact: next sentence after the error
                for j in range(i + 1, min(i + 3, len(sentences))):
                    ns = sentences[j].strip()
                    if len(ns) > 10 and not SubPatternExtractor._is_narrative_noise(ns):
                        impacts.append(ns[:100])
                        break
                break

        if not error:
            return None

        outcome = SubPatternExtractor._detect_outcome(text)
        return SubPatternExtractor._build_chain(intent, error, impacts, None, outcome)

    @staticmethod
    def _detect_outcome(text: str) -> str | None:
        """Detect whether the issue was resolved or remains open."""
        tl = text.lower()
        # Resolution indicators
        if re.search(r'\b(?:resolved|fixed|working|succeeded|success|now\s+(?:works|working|passes)|deployed|complete)\b', tl):
            return "resolved"
        # Unresolved indicators
        if re.search(r'\b(?:unresolved|still\s+(?:fails?|blocked|broken)|pending|ongoing|needs?\s+(?:manual|reboot|restart))\b', tl):
            return "unresolved"
        return None

    @staticmethod
    def _build_chain(intent: str | None, error: str, impacts: list[str],
                     remediation: str | None, outcome: str | None) -> str:
        """Assemble components into a causal chain string."""
        parts = []
        if intent:
            parts.append(intent[:80])
        parts.append(error[:120])
        if remediation:
            parts.append(f"fixed by: {remediation[:80]}")
        if impacts:
            parts.append("impact: " + " | ".join(impacts[:2])[:100])
        if outcome:
            parts.append(f"[{outcome}]")
        return " -> ".join(parts)

    @staticmethod
    def _has_error_indicator(text: str) -> bool:
        tl = text.lower()
        return any(re.search(pat, tl) for pat in SubPatternExtractor.ERROR_INDICATORS)

    @staticmethod
    def _is_narrative_noise(text: str) -> bool:
        tl = text.lower().strip()
        for pat in SubPatternExtractor.NOISE_SENTENCES:
            if re.match(pat, tl):
                return True
        return False


# ═══════════════════════════════════════════════════════════════════
# 3. CROSS-REFERENCER — correlate signals across dimensions
# ═══════════════════════════════════════════════════════════════════

class CrossReferencer:
    """For each domain, compute a signal richness score across dimensions."""

    # Dimensions of signal
    DIMENSIONS = {
        "errors": ["error", "recurring_error", "blocker_narrative"],
        "activity": ["tool_usage", "skill_used", "topic_*"],
        "quality": ["verification", "behavior_test"],
        "knowledge": ["file_narrative", "narrative", "session_summary", "file", "url"],
        "domain_specific": ["domain", "workflow", "artifact_location"],
    }

    @staticmethod
    def richness(domain_signal: dict) -> dict:
        """Compute how many dimensions a domain has signal in."""
        dim_counts = {}
        total = 0
        for dim_name, dim_cats in CrossReferencer.DIMENSIONS.items():
            cnt = 0
            for cat in dim_cats:
                if cat == "topic_*":
                    cnt += sum(
                        len(facts)
                        for c, facts in domain_signal.items()
                        if c.startswith("topic_")
                    )
                else:
                    cnt += len(domain_signal.get(cat, []))
            dim_counts[dim_name] = cnt
            total += cnt
        return {"dimensions": dim_counts, "total_signal_facts": total}


# ═══════════════════════════════════════════════════════════════════
# 4. GOAL INFERENCE — derive production goals from AGENTS.md + patterns
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# 3.5 INTENT EXTRACTOR — directional signals from decisions, principles, trends
# ═══════════════════════════════════════════════════════════════════

class IntentExtractor:
    """Extract directional intent from all available sources:

    1. decisions.jsonl — explicit human decisions (what was divested/migrated/invested)
    2. Minimalist Operations Principle — "could we just remove this?" as first question
    3. Temporal error trends — increasing/decreasing/flat from memory.db timestamps
    4. Recurring error deprioritization — high session count with no fix = low priority
    """

    DECISIONS_PATH = Path.home() / ".factory" / "knowledge" / "decisions.jsonl"

    # Words that signal divestment in decisions
    DIVEST_KEYWORDS = [
        "disband", "deprecat", "remov", "delet", "retir", "abandon",
        "sunset", "kill", "archive", "stop using", "no longer",
    ]
    # Words that signal migration
    MIGRATE_KEYWORDS = ["migrat", "mov", "switch", "replac", "transition"]
    # Words that signal investment
    INVEST_KEYWORDS = ["deploy", "implement", "add", "build", "create", "set up",
                       "wire", "adopt", "integrat"]

    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(str(db_path))
        self.divested: set[str] = set()
        self.invested: set[str] = set()
        self.held: set[str] = set()
        self.deprioritized: set[str] = set()
        self.external_fix: set[str] = set()
        self.divest_targets: dict[str, str] = {}
        self.temporal_trends: dict[str, str] = {}
        self._fix_history: set[str] = set()
        self._fix_cost: dict[str, float] = {}
        self.deprecated_services: dict[str, str] = {}  # broken_service -> replacement
        self.migration_targets: set[str] = set()

    def analyze(self) -> "IntentExtractor":
        """Run all intent extraction passes."""
        self._parse_decisions()
        self._detect_migrations()            # broken→replacement pairs from blocker narratives
        self._compute_fix_feasibility()      # which domains have EVER been fixed?
        self._compute_temporal_trends()
        self._compute_implicit_deprioritization()
        self._compute_session_investment()
        self.db.close()
        return self

    # ─── Migration detection: broken→replacement pairs ───

    REPLACEMENT_SIGNALS = [
        r'(?:use|try|add|switch\s+to|move\s+to)\s+(?:a\s+|an\s+)?(\w+)(?:-based|-powered)?\s+(?:path|approach|solution|alternative|instead|sending)',
        r'(\w+)_(?:API_KEY|TOKEN|SECRET|PASSWORD)\s+is\s+already\s+(?:in|available|set\s+up)',
        r'(?:could|can|should|lets?)\s+(?:we\s+)?(?:use|try|switch\s+to)\s+(\w+)',
    ]

    KNOWN_SERVICES = {
        "netlify", "northflank", "NF", "resend", "sendgrid", "mailgun",
        "doppler", "bitwarden", "hermes", "n8n", "windmill", "steel",
        "stagehand", "playwright", "comet", "trestle", "neo4j", "sourcebot",
        "grafana", "otel", "tempo", "loki", "prometheus", "tailscale",
        "hostinger", "supabase", "vercel", "cloudflare", "aws", "azure",
        "docker", "kubernetes", "helm", "ollama", "perplexity", "tavily",
        "sfrep", "openhands", "sharepoint", "apollo", "groq",
    }

    def _detect_migrations(self):
        """Find broken-service + replacement pairs from blocker narratives."""
        for cat in ["blocker_narrative", "error"]:
            rows = self.db.execute(
                "SELECT content FROM facts WHERE category=? AND status='live'", [cat]
            ).fetchall()
            for (content,) in rows:
                self._detect_replacement_pairs(content)

    def _detect_replacement_pairs(self, text: str):
        """Find pairs of (broken_service, proposed_replacement) in a blocker narrative."""
        tl = text.lower()

        broken_services = set()
        for known in sorted(self.KNOWN_SERVICES, key=len, reverse=True):
            for m in re.finditer(rf'\b{re.escape(known)}\b', text, re.IGNORECASE):
                nearby = text[max(0, m.start()-20):m.end()+120]
                if re.search(r'(?:expired|revoked|401|403|500|timeout|broken|failing|down|unreachable)',
                             nearby, re.IGNORECASE):
                    broken_services.add(known.lower())
                    break

        proposed_replacements = set()
        for pattern in self.REPLACEMENT_SIGNALS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                svc = m.group(1).lower().rstrip('.,;:')
                if svc in self.KNOWN_SERVICES or any(
                    k in svc for k in self.KNOWN_SERVICES if len(k) > 2
                ):
                    proposed_replacements.add(svc)

        available = set()
        for m in re.finditer(r'(\w+)_(?:API_KEY|TOKEN|SECRET|PASSWORD)\s+is\s+already\s+(?:in|available)', tl):
            svc = m.group(1).lower()
            if len(svc) > 1:
                available.add(svc)

        for broken in broken_services:
            for replacement in (proposed_replacements | available):
                if broken != replacement:
                    broken_key = self._normalize_service(broken)
                    rep_key = self._normalize_service(replacement)
                    if broken_key != rep_key:
                        self.deprecated_services[broken_key] = replacement
                        self.migration_targets.add(rep_key)

    @staticmethod
    def _normalize_service(name: str) -> str:
        """Normalize a service name: 'NF' -> 'netlify', 'northflank' -> 'netlify'."""
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9]', '', name)
        known_map = {
            'nf': 'netlify', 'northflank': 'netlify', 'netlify': 'netlify',
            'resend': 'resend', 'sendgrid': 'sendgrid',
            'doppler': 'doppler', 'bitwarden': 'bitwarden',
            'hermes': 'hermes', 'n8n': 'n8n',
            'grafana': 'grafana', 'otel': 'otel',
        }
        return known_map.get(name, name)

    def is_deprecated(self, domain: str) -> str | None:
        """Return replacement target if domain is being deprecated, else None."""
        domain_key = self._normalize_service(domain)
        for deprecated, replacement in self.deprecated_services.items():
            if deprecated in domain_key or domain_key in deprecated:
                return replacement or "unspecified"
        return None

    # ─── Fix feasibility ───

    def _compute_fix_feasibility(self):
        """Compute fix cost per domain: errors/blockers per successful fix.

        A "fix" = a blocker_narrative where the domain appears within 1000 chars
        of a fix-indicating phrase like "fix deployed", "now working", "shipped", etc.
        
        fix_cost = total domain facts / resolutions. inf = never resolved.
        """
        domain_errors = Counter()
        domain_resolutions = Counter()

        # Fix-indicating phrases that people actually use
        FIX_PHRASES = [
            'fix deployed', 'fix complete', 'fix is live', 'fix is deployed',
            'now working', 'now operational', 'is now working', 'is now operational',
            'i fixed', 'i was able to fix', 'we fixed',
            'shipped', 'built & shipped',
            'pr merged', 'pushed to', 'commit',  # code fix delivered
            'blocking issue resolved', 'both blocking issues resolved',
            'resolved the', 'issue resolved',
        ]

        rows = self.db.execute(
            "SELECT category, content FROM facts WHERE status='live' AND "
            "category IN ('error','recurring_error','blocker_narrative','blocker')"
        ).fetchall()
        for cat, content in rows:
            cl = content.lower()

            # Count domain errors
            for known in SignalCollector.TRACKED_DOMAINS:
                domain_key = known.lower().replace("-", "").replace("_", "")
                if domain_key in cl.replace("-", "").replace("_", ""):
                    domain_errors[known] += 1
                    break

            # Count resolutions: domain + fix phrase within 1000 chars
            if cat != 'blocker_narrative':
                continue
            cl_raw = cl.replace("-", "").replace("_", "")
            for known in SignalCollector.TRACKED_DOMAINS:
                domain_key = known.lower().replace("-", "").replace("_", "")
                # Find all domain mentions
                domain_positions = [m.start() for m in re.finditer(re.escape(domain_key), cl_raw)]
                if not domain_positions:
                    continue
                # Check if any fix phrase occurs within 1000 chars of ANY domain mention
                for pos in domain_positions:
                    window = cl[max(0, pos-1000):pos+1000]
                    for phrase in FIX_PHRASES:
                        if phrase in window:
                            domain_resolutions[known] += 1
                            self._fix_history.add(known)
                            break
                    else:
                        continue
                    break

        for domain in domain_errors:
            errors = domain_errors[domain]
            resolutions = domain_resolutions.get(domain, 0)
            if resolutions > 0:
                self._fix_cost[domain] = round(errors / resolutions, 1)
            else:
                self._fix_cost[domain] = float('inf')

    def _compute_implicit_deprioritization(self):
        """Three-way classification for domains with high error-to-fix ratios:

        DIVEST: explicitly decided to move away (decisions.jsonl) → REMOVE
        EXTERNAL-FIX: errors high, but fixes happen outside Factory (github, git) → INVESTIGATE
        DEPRIORITIZED: errors high, never fixed, just worked around (path, timeout) → lower payoff
        """
        domain_errors = Counter()
        domain_fixes = Counter()

        rows = self.db.execute(
            "SELECT category, content FROM facts WHERE status='live' AND "
            "category IN ('error','recurring_error','blocker_narrative')"
        ).fetchall()
        for cat, content in rows:
            cl = content.lower().replace("-", "").replace("_", "")
            for known in SignalCollector.TRACKED_DOMAINS:
                if known.lower().replace("-", "").replace("_", "") in cl:
                    domain_errors[known] += 1
                    break

        # Fixes: verification pass, skill_effectiveness with success/partial,
        # plus fix_history from blocker narratives
        rows = self.db.execute(
            "SELECT content FROM facts WHERE status='live' AND "
            "category IN ('verification','skill_effectiveness')"
        ).fetchall()
        for (content,) in rows:
            cl = content.lower()
            if "pass" in cl or "success" in cl or "outcome=success" in cl:
                for known in SignalCollector.TRACKED_DOMAINS:
                    if known.lower().replace("-", "").replace("_", "") in cl.replace("-", "").replace("_", ""):
                        domain_fixes[known] += 1
                        break

        # Domains where fixes happen on external platforms (github, git, etc.)
        EXTERNAL_FIX_DOMAINS = {"github", "git", "bitwarden", "doppler"}

        for domain, errors in domain_errors.items():
            if errors < 25:
                continue
            tier = SURFACE_TIERS.get(domain, "unclassified")
            alias = SignalCollector.DOMAIN_ALIASES.get(domain, "")
            if alias:
                tier = SURFACE_TIERS.get(alias, tier)
            if tier in ("core", "infra"):
                continue  # never deprioritize core/infra

            fixes = domain_fixes.get(domain, 0)
            ratio = errors / max(fixes, 1)

            if ratio <= 15:
                continue  # reasonable fix rate

            # CLASSIFY based on fix history and domain type
            has_history = domain in self._fix_history

            if domain in EXTERNAL_FIX_DOMAINS:
                # Fixes happen on external platforms — not abandoned, just different workflow
                self.external_fix.add(domain)
            elif has_history:
                # Has been fixed before but keeps breaking — platform noise, not divestment
                pass  # don't classify — it's fixable but noisy
            else:
                # Never fixed, not external — truly deprioritized
                self.deprioritized.add(domain)

    def _compute_session_investment(self):
        """Domains with the most facts = where the user invests time.

        Top quartile by fact count = active investment areas.
        Bottom quartile with errors = underinvested (not divested, just neglected).
        """
        domain_fact_counts = Counter()
        rows = self.db.execute(
            "SELECT content FROM facts WHERE status='live'"
        ).fetchall()
        for (content,) in rows:
            cl = content.lower().replace("-", "").replace("_", "")
            for known in SignalCollector.TRACKED_DOMAINS:
                if known.lower().replace("-", "").replace("_", "") in cl:
                    domain_fact_counts[known] += 1
                    break

        if not domain_fact_counts:
            return

        # Top 25% by fact count = clearly invested
        counts = [c for c in domain_fact_counts.values() if c >= 10]
        if counts:
            threshold = sorted(counts)[-max(1, len(counts) // 4)]
            for domain, cnt in domain_fact_counts.items():
                if cnt >= threshold and domain not in self.divested:
                    self.invested.add(domain)

    def _parse_decisions(self):
        """Parse decisions.jsonl for divestment, migration, investment signals."""
        if not self.DECISIONS_PATH.exists():
            return

        with open(self.DECISIONS_PATH) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                decision = (d.get("decision") or d.get("chosen") or "").lower()
                rationale = (d.get("rationale") or "").lower()
                combined = f"{decision} {rationale}"

                # Detect divestment: "Disbanded X", "Removed Y"
                if any(kw in combined for kw in self.DIVEST_KEYWORDS):
                    targets = self._extract_nearby_nouns(decision, self.DIVEST_KEYWORDS)
                    for t in targets:
                        self.divested.add(t)

                # Detect migration: "Migrated X to Y"
                if any(kw in combined for kw in self.MIGRATE_KEYWORDS):
                    targets = self._extract_nearby_nouns(decision, self.MIGRATE_KEYWORDS)
                    for t in targets:
                        self.divested.add(t)

                # Detect intentional holds: "Built but did NOT run/start"
                if re.search(r'built\s+.*\b(?:but|did)\s+not\s+(?:run|start|deploy)', combined):
                    targets = self._extract_nearby_nouns(decision, ["built"])
                    for t in targets:
                        self.held.add(t)

                # Detect investment: "Deployed X", "Added Y"
                # Skip if already divested — divestment always wins
                if any(kw in combined for kw in self.INVEST_KEYWORDS):
                    targets = self._extract_nearby_nouns(decision, self.INVEST_KEYWORDS)
                    for t in targets:
                        if t not in self.divested:
                            self.invested.add(t)

    def _extract_nearby_nouns(self, text: str, keywords: list[str]) -> set[str]:
        """Extract domain-like nouns near decision keywords.
        
        Only match compound names, not single-word matches that appear in
        many unrelated decisions (like 'docker', 'legion', 'ms01').
        """
        targets = set()
        # Only match multi-word domain names or very specific single names
        domain_patterns = [
            r'\b(docker\s*desktop)\b',
            r'\b(docker[- ]ce)\b',
            r'\b(sales\s*(?:domain\s*)?driver(?:\s*system)?)\b',
            r'\b(motto[- ](?:video|social|sdr)[- ]?agent)\b',
            r'\b(mission[- ]?control)\b',
            r'\b(pipeline[- ]?stack)\b',
            r'\b(exit[- ]?node)\b',
            r'\b(opentelemetry\s*collector)\b',
            r'\b(neo4j\s*mcp)\b',
        ]
        for pat in domain_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                # Normalize: "docker-desktop" or "docker desktop" → "docker-desktop"
                name = m.group(1).lower()
                name = re.sub(r'\s+', '-', name)
                targets.add(name)
        return targets

    def _compute_temporal_trends(self):
        """Compute error frequency trends per domain from memory.db.
        
        "rising" = errors increased in last 2 weeks vs prior 2 weeks
        "falling" = errors decreased
        "flat" = no significant change or no data
        """
        now = datetime.now()
        recent = (now - timedelta(days=14)).isoformat()[:10]
        prior_start = (now - timedelta(days=28)).isoformat()[:10]
        prior_end = (now - timedelta(days=14)).isoformat()[:10]

        # Get error facts grouped by domain and time window
        rows = self.db.execute(
            "SELECT content, created_at FROM facts WHERE category IN ('error','recurring_error','blocker_narrative') AND status='live'"
        ).fetchall()

        # Aggregate by domain and window
        domain_recent = defaultdict(int)
        domain_prior = defaultdict(int)
        for content, created_at in rows:
            ts = (created_at or "")[:10]
            cl = content.lower()
            # Determine domain from content keywords
            for known in SignalCollector.TRACKED_DOMAINS:
                if known.lower().replace("-", "").replace("_", "") in cl.replace("-", "").replace("_", ""):
                    if ts >= recent:
                        domain_recent[known] += 1
                    elif prior_start <= ts < prior_end:
                        domain_prior[known] += 1
                    break  # first domain match only

        # Compute trends — only flag when difference is substantial
        for domain in set(list(domain_recent.keys()) + list(domain_prior.keys())):
            rec = domain_recent.get(domain, 0)
            prior = domain_prior.get(domain, 0)
            # Require sustained error volume AND significant change
            if rec >= 5 and rec > prior * 2.0:
                self.temporal_trends[domain] = "rising"
            elif prior >= 5 and prior > rec * 2.0:
                self.temporal_trends[domain] = "falling"
            elif rec >= 5 or prior >= 5:
                self.temporal_trends[domain] = "flat"

    # ─── Query methods used by the pipeline ───

    def should_remove(self, domain: str, tier: str) -> bool:
        """Minimalist Operations Principle: could we just remove this?"""
        # Tier-based: experimental → always remove
        if tier == "experimental":
            return True
        # Explicitly divested (moving away from platform)
        if self.is_divested(domain):
            return True
        # Deprioritized with no fix history → candidate for removal
        if self.is_deprioritized(domain):
            return True
        # Unclassified with flat/falling trends and no investment → candidate
        if tier == "unclassified":
            trend = self.temporal_trends.get(domain, "")
            if trend in ("flat", "falling") and not self.is_invested(domain):
                return True
        return False

    def is_divested(self, domain: str) -> bool:
        """Explicitly moving away from this platform (decisions.jsonl)."""
        domain_key = domain.lower().replace("-", "").replace("_", "")
        for d in self.divested:
            if d.lower().replace("-", "").replace("_", "") == domain_key:
                return True
        return False

    def is_external_fix(self, domain: str) -> bool:
        """Fixes happen outside Factory (github, git, etc.)."""
        domain_key = domain.lower().replace("-", "").replace("_", "")
        for d in self.external_fix:
            if d.lower().replace("-", "").replace("_", "") == domain_key:
                return True
        return False

    def is_deprioritized(self, domain: str) -> bool:
        """Errors worked around, never fixed, no replacement."""
        domain_key = domain.lower().replace("-", "").replace("_", "")
        for d in self.deprioritized:
            if d.lower().replace("-", "").replace("_", "") == domain_key:
                return True
        return False

    def is_invested(self, domain: str) -> bool:
        domain_key = domain.lower().replace("-", "").replace("_", "")
        for d in self.invested:
            if d.lower().replace("-", "").replace("_", "") == domain_key:
                return True
        return False

    def is_held(self, domain: str) -> bool:
        domain_key = domain.lower().replace("-", "").replace("_", "")
        for d in self.held:
            if d.lower().replace("-", "").replace("_", "") == domain_key:
                return True
        return False

    def trend(self, domain: str) -> str:
        return self.temporal_trends.get(domain, "")

    def fix_cost(self, domain: str) -> float:
        """Sessions/errors per resolution. inf = never resolved."""
        domain_key = domain.lower().replace("-", "").replace("_", "")
        for d, cost in self._fix_cost.items():
            if d.lower().replace("-", "").replace("_", "") == domain_key:
                return cost
        return float('inf')
class GoalInference:
    """Infer production goals from AGENTS.md tier assignments and memory.db patterns.

    Each goal has a criticality weight (0-1) used in payoff scoring.
    Goals are derived, not hand-coded — they emerge from the existing tier system
    and cross-machine topology described in AGENTS.md.
    """

    # Goal definitions — derived from AGENTS.md surface tiers + Minimalist Operations Principle
    GOALS = {
        "revenue-continuity": {
            "label": "Revenue Continuity",
            "description": "Appraisal pipeline must not break — sfrep, stagehand, tax portals",
            "criticality": 1.0,
            "surfaces": {"sfrep-mcp", "sfrep", "stagehand", "taxnet", "ntreis", "truetracts",
                         "appraisal-pipeline", "sdr-agent", "order-monitor", "bidding"},
        },
        "infra-health": {
            "label": "Infrastructure Health",
            "description": "Operational visibility — hermes, grafana, otel, docker, tailscale",
            "criticality": 0.7,
            "surfaces": {"hermes", "grafana", "otel", "tempo", "docker", "tailscale",
                        "mcp-server", "fleet-triage", "director"},
        },
        "credential-health": {
            "label": "Credential Health",
            "description": "Secrets must be current — expired tokens cascade-fail everything",
            "criticality": 0.9,
            "surfaces": {"doppler", "bitwarden", "credential", "credential-grabber", "auth-sso"},
        },
        "cross-machine": {
            "label": "Cross-Machine Connectivity",
            "description": "Both machines must be reachable via SSH + Tailscale",
            "criticality": 0.8,
            "surfaces": {"ssh", "wsl", "tailscale", "hostinger"},
        },
        "surface-hygiene": {
            "label": "Surface Hygiene",
            "description": "Dead surfaces must be removed — Minimalist Operations Principle",
            "criticality": 0.5,
            "surfaces": {"n8n", "windmill", "optimization-db", "comet", "steel", "netlify"},
        },
        "behavior-compliance": {
            "label": "Behavior Compliance",
            "description": "Safety rules must be enforced — guardrails protect real ops",
            "criticality": 0.6,
            "surfaces": set(),
        },
        "migration-completion": {
            "label": "Migration Completion",
            "description": "Finish removing deprecated services — remove token, archive code",
            "criticality": 0.85,
            "surfaces": set(),  # populated dynamically from IntentExtractor
        },
    }

    _intent = None

    @classmethod
    def set_intent(cls, intent):
        cls._intent = intent

    @classmethod
    def tag_issue(cls, domain: str, tier: str, recommendation: str) -> list[tuple[str, float]]:
        """Return [(goal_key, goal_criticality)] for an issue.
        
        Migration-aware: if a service is being deprecated, reclassify
        from "fix it" to "finish the migration."
        """
        tags = []
        for goal_key, goal in cls.GOALS.items():
            if domain.lower().replace("-", "").replace("_", "") in {
                s.lower().replace("-", "").replace("_", "") for s in goal["surfaces"]
            }:
                tags.append((goal_key, goal["criticality"]))
        
        # Behavior tests always get behavior-compliance
        if tier == "behavior":
            tags.append(("behavior-compliance", 0.6))
        
        # REMOVE on experimental always gets surface-hygiene
        if recommendation == "REMOVE" and tier == "experimental":
            tags.append(("surface-hygiene", 0.5))
        
        # Migration awareness: deprecated services get reclassified
        if cls._intent:
            dep_target = cls._intent.is_deprecated(domain)
            if dep_target:
                # Override: this isn't about fixing the broken thing —
                # it's about completing the migration away from it
                tags = [("migration-completion", 0.85)]
                if dep_target != "unspecified":
                    tags.append(("revenue-continuity", 0.6))  # migration unblocks the replacement
        
        return tags

    @classmethod
    def primary_goal(cls, domain: str, tier: str, recommendation: str) -> str:
        """Return the primary production goal this issue supports."""
        tags = cls.tag_issue(domain, tier, recommendation)
        if not tags:
            return "general-maintenance"
        return max(tags, key=lambda t: t[1])[0]

    # ─── Specific goal derivation (merged from GoalDeriver) ───

    INTENT_MARKERS = [
        (r'(?:demo|production|live|test)\s+run:\s*(.{10,80})', "Running"),
        (r'(?:pipeline|workflow)\s+(?:ran|executed)\s+(.{10,80})', "Executing"),
        (r'(?:deploy|push)\s+(?:to\s+)?(.{10,80})', "Deploying"),
        (r'(?:build|compile)\s+(.{10,80})', "Building"),
        (r'(?:migrat|mov|switch)(?:ing|ed)?\s+(?:from|away)\s+(.{10,80})', "Migrating from"),
    ]

    @staticmethod
    def derive(domain: str, sub_patterns: list[tuple[str, int]],
               is_deprecated: bool = False,
               dep_target: str | None = None) -> str:
        """Derive a specific, actionable goal from causal chains."""
        if not sub_patterns:
            return ""

        best_chain, best_count = sub_patterns[0]

        intent = None
        error = None

        parts = re.split(r'\s*[-—>]+\s*|\s*->\s*', best_chain, maxsplit=2)
        if parts:
            first = parts[0].strip()
            first = re.sub(r'^\[?\d+x\]?\s*', '', first)
            first = re.sub(r'^error:\s*', '', first)
            if len(first) > 5 and not re.match(r'^(?:what|the|a|an|if|this|that|here|there)\b', first.lower()):
                intent = first[:100].rstrip('.:;-')

        for part in parts[1:]:
            part = part.strip()
            if re.search(r'\b(?:fail|error|block|cannot|unable|expired|broken|401|403|500|timeout)\b',
                         part, re.IGNORECASE):
                error = part[:100].rstrip('.:;-')
                break
        if not error and len(parts) > 1:
            error = parts[1].strip()[:100].rstrip('.:;-')

        if not error and not intent:
            return ""

        if is_deprecated:
            target = dep_target or "the replacement"
            if error and "expired" in error.lower():
                return f"Remove {domain} dependency — {target} migration (token expired, no fix needed)"
            return f"Complete {domain}→{target} migration"

        if intent and error:
            intent_short = intent[:60].rstrip('.:;-')
            error_short = re.sub(r'^(?:failed|error|blocked)(?:\s+(?:at|with|on|by|in))?\s*', '', error, flags=re.IGNORECASE)[:60]
            error_short = error_short.rstrip('.:;-')
            if len(intent_short) < 10:
                return f"Fix: {error_short[:80]}"
            return f"Restore {intent_short[:50]} (blocked: {error_short[:50]})"

        if error:
            return f"Fix: {error[:90]}"

        if intent:
            return f"Enable: {intent[:90]}"

        return ""


# ═══════════════════════════════════════════════════════════════════
# 5. PAYOFF SCORER — quantitative remediation ROI
# ═══════════════════════════════════════════════════════════════════

class PayoffScorer:
    """Compute quantitative remediation payoff: (Impact × Confidence) / Cost.

    Higher = more urgent to fix. All components are numeric, not categorical.
    """

    @staticmethod
    def compute(domain: str, tier: str, recommendation: str,
                confidence_score: float, signal_richness: int,
                session_count: int, error_count: int, is_engine_dep: bool,
                sub_pattern_count: int,
                is_deprecated: bool = False,
                is_divested: bool = False,
                is_deprioritized: bool = False,
                is_external_fix: bool = False,
                is_invested: bool = False,
                trend: str = "",
                fix_cost: float = float('inf')) -> float:
        """Return a payoff score.

        fix_cost = errors per resolution event. inf = never resolved.
        High fix cost → expensive to fix → lowers payoff.
        """

        # --- IMPACT (0-10) ---
        tier_impact = {"core": 5.0, "infra": 3.0, "experimental": 1.0, "unclassified": 1.5}.get(tier, 1.0)

        if is_divested:
            tier_impact = 0.5
        elif is_deprecated:
            tier_impact = 2.0
        elif is_deprioritized:
            tier_impact = 1.0
        elif is_invested:
            tier_impact = min(6.0, tier_impact * 1.3)

        if trend == "rising":
            tier_impact *= 1.2
        elif trend == "falling":
            tier_impact *= 0.7

        volume_impact = min(3.0, (signal_richness ** 0.4) * 0.3)
        session_impact = min(2.0, session_count * 0.05)
        error_impact = min(1.5, error_count * 0.3)
        goals = GoalInference.tag_issue(domain, tier, recommendation)
        goal_impact = max((g[1] for g in goals), default=0.3) * 2.0
        engine_impact = 1.0 if is_engine_dep else 0.0

        impact = min(10.0, tier_impact + volume_impact + session_impact +
                     error_impact + goal_impact + engine_impact)

        confidence = confidence_score

        # --- COST ---
        if is_divested or is_deprecated:
            cost = 0.15
        elif is_deprioritized:
            cost = 0.25
        elif is_external_fix:
            cost = 0.5
        elif recommendation == "REMOVE":
            cost = 0.2
        elif recommendation == "DISMISS":
            cost = 0.1
        elif error_count > 3 and sub_pattern_count > 1:
            cost = 0.4
        elif error_count > 0:
            cost = 0.5
        elif tier == "experimental":
            cost = 0.6
        else:
            cost = 0.7

        # Fix cost adjustment: expensive domains have higher cost
        if fix_cost != float('inf') and fix_cost > 10:
            cost *= min(2.0, fix_cost / 10)  # 20:1 fix ratio = 2x cost

        if is_engine_dep:
            cost *= 0.7

        payoff = (impact * confidence) / max(cost, 0.1)
        return round(payoff, 2)


# ═══════════════════════════════════════════════════════════════════
# 6. MEMORY COLLABORATOR — deep context from memory system
# ═══════════════════════════════════════════════════════════════════

class MemoryCollaborator:
    """Collaborate with the memory system for deep context on high-signal domains."""

    @staticmethod
    def deep_context(domain: str, session_count: int) -> list[str]:
        snippets = []
        if session_count < 5:
            return snippets
        try:
            result = subprocess.run(
                ["python", str(FACTORY / "scripts" / "full-session-search.py"),
                 "search", f"{domain} errors failures"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.split("\n")[:3]:
                    if line.strip() and len(line) > 10:
                        snippets.append(line.strip()[:150])
        except Exception:
            pass
        return snippets


# 5. MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════

def run_funnel():
    # Phase 0a: Intent extraction — decisions.jsonl + temporal trends + Minimalist Principle
    intent = IntentExtractor(DB_PATH).analyze()
    if intent.divested:
        print(f"Divested (moving away from platform): {', '.join(sorted(intent.divested)[:8])}")
    if intent.deprioritized:
        print(f"Deprioritized (worked around, never fixed): {', '.join(sorted(intent.deprioritized)[:8])}")
    if intent.external_fix:
        print(f"External-fix (fixes happen outside Factory): {', '.join(sorted(intent.external_fix)[:8])}")
    if intent.invested:
        print(f"Active investment: {', '.join(sorted(intent.invested)[:8])}")
    if intent.held:
        print(f"Intentionally dormant: {', '.join(sorted(intent.held)[:5])}")
    trending = [(d, t) for d, t in intent.temporal_trends.items() if t in ("rising", "falling")]
    if trending:
        print(f"Temporal trends: {', '.join(f'{d}({t})' for d, t in trending[:6])}")

    # Migration detection is now part of intent.analyze()
    GoalInference.set_intent(intent)
    if intent.deprecated_services:
        print(f"Detected migrations: {', '.join(f'{k}->{v}' for k,v in list(intent.deprecated_services.items())[:5])}")
    if intent.migration_targets:
        print(f"  Migration targets: {', '.join(sorted(intent.migration_targets)[:5])}")
    print()

    # Phase 1: Collect
    collector = SignalCollector(DB_PATH).collect()
    print(f"Collected signal across {len(collector.domains)} domains from {sum(collector.fact_counts.values())} facts\n")

    # Phase 2: For each domain with signal, extract + cross-reference + audit
    all_issues = []

    for domain, signal in sorted(collector.domains.items()):
        total_facts = sum(len(v) for v in signal.values())

        # Minimalist Operations Principle: dormant domains → REMOVE
        if total_facts < 5 and domain not in intent.invested:
            tier = SURFACE_TIERS.get(domain, "unclassified")
            # Skip noise domains
            if domain in SignalCollector.NOISE_DOMAINS:
                continue
            all_issues.append({
                "domain": domain,
                "tier": tier,
                "recommendation": "REMOVE",
                "confidence": "medium",
                "score": 0.5,
                "payoff": 2.0 if tier == "experimental" else 1.0,
                "goal": "surface-hygiene",
                "derived_goal": f"Remove dormant surface: {domain} ({total_facts} facts, no active investment)",
                "goal_criticality": 0.4,
                "signal_richness": {"dimensions": {}, "total_signal_facts": total_facts},
                "sub_patterns": [(f"Dormant: {total_facts} facts, below removal threshold", 1)],
                "rationale": f"Dormant surface with {total_facts} facts — Minimalist Operations Principle: remove unless invested",
                "narrative": "",
                "engine_dep": False,
                "github": {"issues": 0, "duplicates": [], "ci_failures": [], "stale_prs": 0},
                "intent_divested": False,
                "intent_invested": False,
                "intent_held": False,
                "trend": "",
            })
            continue

        # Skip domains with very low signal (retaining the existing 3-fact floor)
        if total_facts < 3:
            continue

        tier = SURFACE_TIERS.get(domain, "unclassified")
        richness = CrossReferencer.richness(signal)
        sub_patterns = SubPatternExtractor.extract(domain, signal)

        # Skip unclassified domains with low signal — not worth filing
        if tier == "unclassified" and richness["total_signal_facts"] < 50:
            continue

        # Build rich payload for deep_audit
        error_count = len(signal.get("error", []))
        blocker_count = len(signal.get("blocker_narrative", []))
        recurring = signal.get("recurring_error", [])
        recurring_count = len(recurring)
        session_count = 0
        if recurring:
            m = re.search(r'sessions=(\d+)', recurring[0]["content"])
            if m:
                session_count = int(m.group(1))

        # Build samples from the richest sources
        samples = []
        if sub_patterns:
            samples = [f"[{cnt}s] {pat[:100]}" for pat, cnt in sub_patterns[:3]]
        if not samples and recurring:
            samples = [recurring[0]["content"][:200]]

        # Cross-reference with GitHub + Neo4j (external signal sources)
        github_ctx = GitHubScanner.scan(domain)
        neo4j_ctx = {} if not Neo4jScanner.available() else {"stale": "neo4j unreachable — Docker down on ms01"}

        payload = {
            "signal_class": "pipeline-blocker",
            "domain": domain,
            "error_count": error_count,
            "blocker_count": blocker_count,
            "recurring_count": recurring_count,
            "session_count": session_count,
            "signal_richness": richness["total_signal_facts"],
            "samples": samples,
            "sub_patterns": sub_patterns,
        }

        # Audit
        item = {"id": f"full-{domain}", "payload": payload}
        try:
            result = audit_item(item)
        except Exception as e:
            print(f"  SKIP {domain}: audit_item error: {e}")
            continue

        narrative = result["narrative"]

        # Extract recommendation
        rec = ""
        m = re.search(r'\*\*Recommendation:\s*(\S+)\*\*', narrative)
        if m:
            rec = m.group(1)

        # Extract rationale
        rationale = ""
        for line in narrative.split("\n"):
            if "beats" in line.lower():
                rationale = line.strip()[:150]
                break

        # Intent-driven recommendation override
        effective_rec = rec
        if intent.should_remove(domain, tier):
            effective_rec = "REMOVE"
        elif intent.is_held(domain) and rec == "FIX":
            effective_rec = "DISMISS"
        elif intent.is_external_fix(domain) and rec == "REMOVE":
            effective_rec = "INVESTIGATE"  # external-fix never gets REMOVE

        # Quantitative remediation payoff: (Impact × Confidence) / Cost
        is_dep = intent.is_deprecated(domain) is not None
        # Also check: do the sub_patterns mention any deprecated service?
        if not is_dep:
            all_text = " ".join(pat for pat, _ in sub_patterns)
            al = all_text.lower()
            for deprecated, replacement in intent.deprecated_services.items():
                deprecated_norm = intent._normalize_service(deprecated)
                if deprecated_norm in al or deprecated in al:
                    is_dep = True
                    break
                if deprecated_norm == "netlify" and re.search(r'\bnf\b', al):
                    is_dep = True
                    break
        payoff = PayoffScorer.compute(
            domain=domain, tier=tier, recommendation=effective_rec,
            confidence_score=result.get("confidence_score", 0.5),
            signal_richness=richness["total_signal_facts"],
            session_count=session_count, error_count=error_count,
            is_engine_dep=_is_engine_dependency(domain),
            sub_pattern_count=len(sub_patterns),
            is_deprecated=is_dep,
            is_divested=intent.is_divested(domain),
            is_deprioritized=intent.is_deprioritized(domain),
            is_external_fix=intent.is_external_fix(domain),
            is_invested=intent.is_invested(domain),
            trend=intent.trend(domain),
            fix_cost=intent.fix_cost(domain),
        )

        # Production goal alignment — migration-aware
        if is_dep:
            goal = "migration-completion"
            goal_criticality = GoalInference.GOALS["migration-completion"]["criticality"]
        else:
            goal = GoalInference.primary_goal(domain, tier, rec)
            goal_tags = GoalInference.tag_issue(domain, tier, rec)
            goal_criticality = max((g[1] for g in goal_tags), default=0.3)

        # Derive specific outcome goal from causal chains (not topic bucket)
        derived_goal = GoalInference.derive(
            domain, sub_patterns,
            is_deprecated=is_dep,
            dep_target=intent.is_deprecated(domain) if intent.is_deprecated(domain) else None,
        )

        # Build domain context once, then explode into per-sub-pattern issues
        domain_context = {
            "domain": domain,
            "tier": tier,
            "effective_rec": effective_rec,
            "confidence": result["confidence"],
            "confidence_score": result.get("confidence_score", 0),
            "is_deprecated": is_dep,
            "dep_target": intent.is_deprecated(domain) if intent.is_deprecated(domain) else None,
            "goal": goal,
            "derived_goal": derived_goal,
            "goal_criticality": goal_criticality,
            "signal_richness": richness,
            "github_ctx": github_ctx,
            "rationale": rationale,
            "narrative": narrative,
            "engine_dep": _is_engine_dependency(domain),
            "intent_divested": intent.is_divested(domain),
            "intent_invested": intent.is_invested(domain),
            "intent_held": intent.is_held(domain),
            "intent_deprioritized": intent.is_deprioritized(domain),
            "intent_external_fix": intent.is_external_fix(domain),
            "fix_cost": intent.fix_cost(domain),
            "trend": intent.trend(domain),
        }

        if sub_patterns:
            # One issue per sub-pattern — each gets the domain's full payoff
            for idx, (pat, cnt) in enumerate(sub_patterns):
                clean = _clean_pattern(pat)
                # Skip noise-only sub-patterns
                if _is_noise_subpattern(clean):
                    continue
                sub_title = _short_title(domain, pat)
                all_issues.append({
                    **domain_context,
                    "recommendation": effective_rec,
                    "payoff": payoff,  # keep full domain payoff — each sub-issue is equally urgent
                    "sub_patterns": [(pat, cnt)],
                    "title": sub_title,
                    "is_sub_issue": True,
                })
        else:
            # Fallback: domain-level issue with no sub-patterns
            all_issues.append({
                **domain_context,
                "recommendation": effective_rec,
                "payoff": payoff,
                "sub_patterns": [],
                "title": domain,
                "is_sub_issue": False,
            })

    # Add behavior test issues (deduplicated)
    behavior_seen = set()
    for cat in ("behavior_test",):
        for content, _, _ in collector.raw_facts.get(cat, []):
            m = re.search(r'behavior_test:(\S+)\s+verdict=(\S+)\s+score=([\d.]+)', content)
            if m and m.group(2) == "fail":
                probe = m.group(1)
                if probe in behavior_seen:
                    continue
                behavior_seen.add(probe)
                score_val = float(m.group(3))
                item = {"id": f"full-behav-{probe}", "payload": {
                    "signal_class": "behavior-fix", "probe": probe, "score": score_val,
                }}
                try:
                    result = audit_item(item)
                except Exception:
                    continue
                narrative = result["narrative"]
                rec = ""
                m2 = re.search(r'\*\*Recommendation:\s*(\S+)\*\*', narrative)
                if m2:
                    rec = m2.group(1)
                rationale = ""
                for line in narrative.split("\n"):
                    if "beats" in line.lower():
                        rationale = line.strip()[:150]
                        break
                all_issues.append({
                    "domain": probe,
                    "tier": "behavior",
                    "recommendation": rec,
                    "confidence": result["confidence"],
                    "score": result.get("confidence_score", 0),
                    "payoff": PayoffScorer.compute(
                        domain=probe, tier="behavior", recommendation=rec,
                        confidence_score=result.get("confidence_score", 0.5),
                        signal_richness=1, session_count=0, error_count=1,
                        is_engine_dep=False, sub_pattern_count=0,
                        is_deprecated=False,
                    ),
                    "goal": "behavior-compliance",
                    "goal_criticality": 0.6,
                    "signal_richness": {"dimensions": {"behavior": 1}, "total_signal_facts": 1},
                    "sub_patterns": [],
                    "rationale": rationale,
                    "narrative": narrative,
                    "engine_dep": False,
                })

    # Phase 3: Add neo4j issues (code graph health)
    if Neo4jScanner.available():
        neo4j_issues = Neo4jScanner.repo_issues()
        all_issues.extend(neo4j_issues)

    # Phase 3b: Add OTEL issues (container health from Prometheus metrics)
    otel_issues = OTELScanner.container_issues()
    all_issues.extend(otel_issues)
    otel_summary = OTELScanner.metrics_summary()

    # Phase 3c: Add CI failure issues (from ALL lkmotto repos, not just 6)
    ci_failures = GitHubScanner.global_ci_summary()
    ci_seen = set()
    for cf in ci_failures:
        key = f"{cf['repo']}:{cf['name']}"
        if key in ci_seen:
            continue
        ci_seen.add(key)
        all_issues.append({
            "domain": f"ci-{cf['repo']}",
            "tier": "infra",
            "recommendation": "INVESTIGATE",
            "confidence": "high",
            "score": 0.85,
            "payoff": 5.5,
            "goal": "infra-health",
            "goal_criticality": 0.7,
            "signal_richness": {"dimensions": {"github": 1}, "total_signal_facts": 1},
            "sub_patterns": [(f"CI failure: {cf['name']} on {cf['branch']} ({cf['date']})", 1)],
            "rationale": f"CI failed on {cf['repo']}/{cf['branch']} — {cf['name'][:80]}",
            "narrative": "",
            "engine_dep": False,
            "github": {"ci_failures": [cf]},
        })

    # Phase 4: Rank by payoff (quantitative remediation ROI)
    all_issues.sort(key=lambda x: x["payoff"], reverse=True)

    # Phase 4: Display — sub-issues with plain language, no jargon
    print()
    print("=" * 100)
    print(f"  FULL-SPECTRUM ISSUE FUNNEL")
    print(f"  {len(all_issues)} issues from {sum(collector.fact_counts.values())} facts across {len(collector.domains)} domains")
    print("=" * 100)

    displayed = 0
    for issue in all_issues:
        domain = issue["domain"]
        tier = issue["tier"]
        rec = issue["recommendation"]
        payoff = issue["payoff"]
        subs = issue.get("sub_patterns", [])
        richness = issue.get("signal_richness", {}).get("total_signal_facts", 0) if isinstance(issue.get("signal_richness"), dict) else 0

        if payoff > 8:
            prio = "P1"
        elif payoff > 4:
            prio = "P2"
        elif payoff > 2:
            prio = "P3"
        else:
            prio = "P4"

        if tier == "unclassified" and richness < 100 and prio == "P4":
            continue

        displayed += 1

        # ── Plain-language intent description ──
        intent_desc_parts = []
        if intent.is_divested(domain):
            intent_desc_parts.append("you decided to move away from this")
        if intent.is_deprecated(domain):
            target = intent.is_deprecated(domain) or "a replacement"
            intent_desc_parts.append(f"migrating to {target}")
        if intent.is_invested(domain):
            intent_desc_parts.append("actively invested in this area")
        if intent.is_deprioritized(domain):
            intent_desc_parts.append("errors are worked around, never fixed")
        if intent.is_external_fix(domain):
            intent_desc_parts.append("fixes happen outside Factory")
        trend_val = issue.get("trend", "")
        if trend_val == "rising":
            intent_desc_parts.append("errors are increasing")
        elif trend_val == "falling":
            intent_desc_parts.append("errors are declining")

        fc = issue.get("fix_cost", float('inf'))
        fix_cost_str = ""
        if fc != float('inf') and fc > 0:
            if fc < 5:
                fix_cost_str = f"cheap to fix ({fc:.0f}:1)"
            elif fc < 15:
                fix_cost_str = f"moderate effort to fix ({fc:.0f}:1)"
            else:
                fix_cost_str = f"expensive to fix ({fc:.0f}:1 — many sessions per resolution)"
        elif not intent.is_external_fix(domain) and not intent.is_divested(domain):
            fix_cost_str = "never successfully resolved"

        # ── Issue header ──
        title = issue.get("title", domain)
        print()
        print("-" * 100)
        payoff_bar = "█" * min(int(payoff), 15)
        print(f"  {prio}  payoff={payoff:4.1f} {payoff_bar}  {rec:<12}  {title[:90]}")
        print(f"        domain: {domain}  |  tier: {tier}  |  {richness} facts")
        if intent_desc_parts:
            print(f"        {'. '.join(intent_desc_parts)}.")
        if fix_cost_str:
            print(f"        {fix_cost_str}.")

        # ── Goal ──
        dg = issue.get("derived_goal", "")
        goals = GoalInference.tag_issue(domain, tier, rec)
        if dg:
            print(f"\n    Goal: {dg[:140]}")
        elif goals:
            goal_labels = [f"{GoalInference.GOALS.get(g[0], {}).get('label', g[0])} ({g[1]:.2f})" for g in goals[:2]]
            print(f"\n    Goals: {', '.join(goal_labels)}")

        # ── Sub-issues ──
        if subs:
            pat, cnt = subs[0]
            clean = _clean_pattern(pat)
            print(f"\n    [{cnt}x] {clean[:140]}")

        # ── Pros/Cons ──
        if rec == "FIX":
            _show_pros_cons_fix(domain, tier, goals, intent)
        elif rec == "REMOVE":
            _show_pros_cons_remove(domain, tier, goals, intent)
        elif rec == "MIGRATE" or intent.is_deprecated(domain):
            _show_pros_cons_migrate(domain, intent.is_deprecated(domain) or "replacement", goals)
        elif rec == "INVESTIGATE":
            _show_pros_cons_investigate(domain, tier, goals)

        # GitHub context
        gh = issue.get("github_ctx", issue.get("github", {}))
        ci_fails = gh.get("ci_failures", [])
        if ci_fails:
            relevant_ci = [cf for cf in ci_fails if domain.lower().replace('-','') in cf['repo'].lower().replace('-','')]
            if relevant_ci:
                print(f"\n    GitHub CI failing: {relevant_ci[0]['repo']} — {relevant_ci[0]['name'][:60]}")

    # ── Strategic Synthesis: theme-level direction, not plumbing ──
    themes = _synthesize_strategy(all_issues, intent, collector)

    # ── Surface probes: what does the system think about key surfaces? ──
    _probe_surfaces(intent, collector)

    # Summary
    print()
    print("=" * 100)
    print(f"  SUMMARY ({displayed}/{len(all_issues)} displayed)")

    fixes = [i for i in all_issues if i["recommendation"] == "FIX"]
    removes = [i for i in all_issues if i["recommendation"] == "REMOVE"]
    consolidates = [i for i in all_issues if i["recommendation"] == "CONSOLIDATE"]
    investigates = [i for i in all_issues if i["recommendation"] == "INVESTIGATE"]
    print(f"  Actions: {len(fixes)} fix, {len(investigates)} investigate, {len(removes)} remove, {len(consolidates)} consolidate")

    urgent = [i for i in all_issues if i["payoff"] > 8]
    important = [i for i in all_issues if 4 < i["payoff"] <= 8]
    nice = [i for i in all_issues if i["payoff"] <= 4]
    print(f"  Urgency: {len(urgent)} urgent (>8), {len(important)} important (4-8), {len(nice)} nice-to-have")

    from collections import Counter
    goal_counts = Counter(i["goal"] for i in all_issues)
    if goal_counts:
        print(f"  Macro goals:  ", end="")
        print(", ".join(f"{GoalInference.GOALS.get(g, {}).get('label', g)}({c})" for g, c in goal_counts.most_common(4)))

    print(f"\n  Sources:  {GitHubScanner.repo_count()} GitHub repos, {len(GitHubScanner.global_ci_summary())} CI failures")
    if otel_summary.get("available"):
        print(f"            {otel_summary['container_count']} containers, {otel_summary['total_metrics']} OTEL metrics")
    else:
        print(f"            OTEL: unreachable")

    print()
    print("=" * 100)

    # ── Self-report: the system tracks itself ──
    _emit_self_report(all_issues, themes, collector, intent)

    return all_issues


def _emit_self_report(all_issues: list, themes: list, collector, intent):
    """Write a fact to memory.db so fleet-triage can see itself in the next run."""
    n_issues = len(all_issues)
    n_themes = len(themes)
    n_surfaces = len(collector.domains)
    now = datetime.now(timezone.utc).isoformat()

    # Build a compact self-report
    recs = Counter(i["recommendation"] for i in all_issues)
    top_payoff = sorted(all_issues, key=lambda x: x["payoff"], reverse=True)[:3]
    top_domains = [f"{i['domain']}({i['payoff']:.0f})" for i in top_payoff]

    content = (
        f"fleet-triage ran {now[:19]}: {n_issues} issues across {n_surfaces} surfaces, "
        f"{n_themes} strategic themes. "
        f"Actions: {dict(recs)}. "
        f"Top domains: {', '.join(top_domains)}. "
        f"{sum(collector.fact_counts.values())} facts ingested, "
        f"{len(intent.invested)} surfaces with active investment."
    )

    import json
    metadata = json.dumps({
        "n_issues": n_issues,
        "n_themes": n_themes,
        "n_surfaces": n_surfaces,
        "recommendations": dict(recs),
        "timestamp": now,
    })

    try:
        db = sqlite3.connect(str(DB_PATH))
        db.execute(
            "INSERT INTO facts (category, content, status, created_at, metadata) VALUES (?, ?, 'live', ?, ?)",
            ("topic_fleet_triage", content, now, metadata),
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"\n  (fleet-triage self-report write failed: {e})")


def _clean_pattern(pat: str) -> str:
    """Strip noise prefixes from a sub-pattern for display."""
    p = pat.strip()
    p = re.sub(r'^\d+x\s*', '', p)
    p = re.sub(r'^error:\s*', '', p)
    p = re.sub(r'^\[BLOCKER from \w+\]\s*', '', p)
    return p


def _synthesize_strategy(all_issues: list, intent, collector) -> list[dict]:
    """Cluster issues into strategic themes and produce directional recommendations.

    Returns list of theme dicts: {name, domains, recommendation, rationale, search_hint}
    """
    # ── Theme definitions: domain clusters + strategic question + answer from external search ──
    THEMES = [
        {
            "name": "Orchestration Consolidation",
            "domains": {"hermes", "n8n", "mission-control", "director", "windmill"},
            "question": "5 orchestration surfaces. Hermes is infra backbone (14.3 payoff). "
                        "n8n and windmill are experimental. Director and mission-control are active. "
                        "Can these consolidate to one or two?",
            "answer": "Industry: n8n leads for flexible self-hosted workflow automation. "
                      "Windmill is developer-centric orchestration (scripts + flows). "
                      "Hermes is homegrown fleet orchestration — no external equivalent exists, "
                      "which means it either earns its place by doing what n8n/windmill can't, "
                      "or it's maintenance overhead for an in-house wheel. "
                      "For a solo operator, one orchestrator plus one specialist is the sweet spot. "
                      "Recommendation: n8n for scheduled workflows + Hermes for fleet state. "
                      "Retire windmill (experimental, never stuck). Director and mission-control "
                      "should fold into Hermes or become n8n workflows if they don't need real-time agent state.",
        },
        {
            "name": "Hostile Portal Strategy",
            "domains": {"truetracts", "ntreis", "taxnet", "stagehand"},
            "question": "3 portals fight browser automation. Truetracts blocked by Google secure-browser. "
                        "NTREIS has Trestle WebAPI (credential pending). TaxNet works via Stagehand. "
                        "Is browser automation sustainable, or pivot to API-first?",
            "answer": "Industry: RESO Web API is now the de facto MLS data standard — NAR-affiliated "
                      "MLSs required to certify against Data Dictionary 2.0 as of April 2025. "
                      "Trestle WebAPI (which implements RESO) is the correct API-first path. "
                      "Browser automation is the fallback, not the primary, for MLS. "
                      "For tax records and parcels (not MLS), county APIs exist but are fragmented; "
                      "browser automation via Stagehand is the practical path for multisource. "
                      "Recommendation: Pivot NTREIS to Trestle WebAPI (credential pending — escalate). "
                      "Keep Stagehand for TaxNet and non-API portals. "
                      "Truetracts is a hostile surface — do not invest further. Find an API alternative "
                      "or accept it as a manual step for now.",
        },
        {
            "name": "Credential Architecture",
            "domains": {"doppler", "bitwarden", "credential-grabber", "credential"},
            "question": "Doppler holds all app secrets. Bitwarden holds portal passwords. "
                        "Credential-grabber retrieves them. Should secrets consolidate to one store "
                        "or is dual-store correct?",
            "answer": "Industry consensus: dual-store is the correct pattern. "
                      "Doppler/Bitwarden/Infisical are app-secret managers (CI/CD, deployments, "
                      "service-to-service). Bitwarden/1Password are human-secret managers "
                      "(passwords, portal logins, API keys a human types). They serve different "
                      "access patterns: machine vs human. HashiCorp Vault is overkill for a solo "
                      "operator — enterprise-grade with complex ACLs. "
                      "Doppler's migration of sending to Resend is a lateral move (email relay "
                      "vs secrets), not a reason to consolidate stores. "
                      "Recommendation: Keep dual-store. Doppler for app secrets, Bitwarden for "
                      "portal passwords. Credential-grabber is the bridge — it reads Bitwarden "
                      "and writes to Doppler when a portal key becomes an app secret. "
                      "This is the correct architecture for a solo operator.",
        },
        {
            "name": "Cross-Machine Resilience",
            "domains": {"ssh", "tailscale", "wsl", "hostinger", "powershell"},
            "question": "SSH over Tailscale has 23:1 fix cost — breaks repeatedly. Tailscale is infra. "
                        "Is there a more resilient connectivity pattern?",
            "answer": "Tailscale is the correct choice for a solo operator — WireGuard-based, "
                      "free for small nets, works across NATs without port forwarding. "
                      "The 23:1 fix cost is a symptom of SSH session management, not Tailscale itself. "
                      "Alternatives: Cloudflare Tunnel (free, but adds a proxy hop and Cloudflare "
                      "dependency). ZeroTier (similar to Tailscale, less polished UI). "
                      "Neither addresses the SSH reliability problem directly. "
                      "Recommendation: Keep Tailscale. Fix the SSH reliability problem at the "
                      "application layer — add a health check daemon that auto-reconnects on drop, "
                      "or switch to Tailscale SSH (built-in, no port 22 needed). "
                      "WSL and PowerShell are local concerns, not network surface problems.",
        },
        {
            "name": "Observability Maturity",
            "domains": {"otel", "tempo", "grafana", "neo4j", "sourcebot"},
            "question": "166 metrics from 12 containers. Tempo traces. Grafana dormant (1 fact). "
                        "Neo4j indexes 61 repos. Earning its keep or overbuilt?",
            "answer": "OTEL + Grafana is the industry standard stack — many solo operators run it. "
                      "The question is whether 12 containers justify 166 metrics with full tracing. "
                      "For comparison, a typical small team runs 20-50 metrics on 5-10 services. "
                      "Grafana being dormant (1 fact in 13000+) is a red flag: either you're not "
                      "looking at dashboards, or the dashboards don't show useful signal. "
                      "Neo4j code graph indexing 61 repos is interesting but not revenue-relevant. "
                      "Recommendation: Trim OTEL to actionable metrics only (Errors, latency, "
                      "saturation). If Grafana has no signal you consult, remove it — Collector "
                      "can push to Tempo alone. Neo4j: keep for code intelligence if it reduces "
                      "session context load (you search code graph instead of reading repos), "
                      "otherwise it's a curiosity, not infrastructure.",
        },
        {
            "name": "Dead Surface Removal",
            "domains": {"optimization-db", "tavily", "comet", "steel", "sharepoint", "email-loe"},
            "question": "These are dormant, experimental, or replaced. The Minimalist Operations "
                        "Principle says remove. Should any be preserved for a reason the data doesn't show?",
            "answer": "Comet: DEAD ancestor tool — replaced by Stagehand. Remove. "
                      "Steel: cloud browser that failed portal auth. Superseded by local Stagehand. Remove. "
                      "optimization-db: personal optimization tracker, cold since creation. "
                      "Archive, don't delete — contains personal data. "
                      "email-loe: Gmail integration for appraisal address parsing. "
                      "BUSINESS CASE: enables appraisal pipeline email routing (indirect revenue). "
                      "Though facts are thin, this surface has a plausible business case — investigate "
                      "value signal gap rather than remove. "
                      "sharepoint: SharePoint document retrieval for appraisal workfiles. "
                      "BUSINESS CASE: enables appraisal document assembly (indirect revenue). "
                      "Though facts are thin, this surface has a plausible business case — investigate "
                      "value signal gap rather than remove. "
                      "tavily: used as MCP tool now, not a managed surface. "
                      "Keep the MCP but remove the surface tracking.",
        },
    ]

    # Score each theme by aggregate issue payoff + intent alignment
    domain_payoffs: dict[str, float] = {}
    domain_tiers: dict[str, str] = {}
    for issue in all_issues:
        d = issue["domain"]
        p = issue["payoff"]
        if d not in domain_payoffs or p > domain_payoffs[d]:
            domain_payoffs[d] = p
        domain_tiers[d] = issue.get("tier", "unclassified")

    results = []
    for theme in THEMES:
        theme_domains = theme["domains"] & set(domain_payoffs.keys())
        if not theme_domains:
            continue

        total_payoff = sum(domain_payoffs.get(d, 0) for d in theme_domains)
        exp_count = sum(1 for d in theme_domains if domain_tiers.get(d) == "experimental")
        infra_count = sum(1 for d in theme_domains if domain_tiers.get(d) == "infra")
        core_count = sum(1 for d in theme_domains if domain_tiers.get(d) == "core")

        # Determine recommendation type
        if core_count >= 2:
            rec = "EVOLVE"  # core surfaces need deliberate evolution
        elif infra_count >= 2:
            rec = "CONSOLIDATE"  # infra surfaces can merge
        elif exp_count >= 2:
            rec = "REMOVE"  # experimental surfaces should go
        elif total_payoff > 30:
            rec = "RESTRUCTURE"  # high payoff = urgent strategic attention
        else:
            rec = "AUDIT"  # investigate before deciding

        results.append({
            "name": theme["name"],
            "domains": sorted(theme_domains),
            "total_payoff": round(total_payoff, 1),
            "question": theme["question"],
            "answer": theme.get("answer", ""),
            "recommendation": rec,
            "core_count": core_count,
            "infra_count": infra_count,
            "exp_count": exp_count,
        })

    results.sort(key=lambda r: r["total_payoff"], reverse=True)

    # Display strategic synthesis
    print()
    print("=" * 100)
    print("  STRATEGIC SYNTHESIS — infrastructure direction, not plumbing")
    print("=" * 100)

    for i, r in enumerate(results):
        print(f"\n  Theme {i+1}: {r['name']}  ({r['recommendation']}, aggregate payoff {r['total_payoff']:.0f})")
        print(f"    Surfaces: {', '.join(r['domains'])}")
        print(f"    ({r['core_count']} core, {r['infra_count']} infra, {r['exp_count']} experimental)")
        print(f"\n    Strategic question: {r['question']}")
        if r.get("answer"):
            print(f"\n    External evidence + recommendation:")
            for line in r["answer"].split("\n"):
                line = line.strip()
                if line:
                    print(f"    {line}")

    return results


def _recycler_search(query: str) -> str:
    """Run a quick recycler search via parts-bin or web search."""
    # Try parts-bin first
    try:
        result = subprocess.run(
            ["python", str(FACTORY / "scripts" / "parts-bin.py"), "search", query],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
            return " | ".join(lines[:2])[:300]
    except Exception:
        pass
    return ""


def _probe_surfaces(intent, collector):
    """Probe the system for its opinion on key surfaces the user is working on."""
    # Surfaces to probe — things the user actively works on or questions
    PROBES = [
        "neo4j",           # code graph — contributory infra but divested MCP layer
        "fleet-triage",    # this system itself — eating its own dogfood
        "docker",          # docker-desktop and docker-ce divested, but docker the platform?
        "stagehand",       # core browser automation — working or fragile?
        "hermes",          # orchestration backbone — is it earning its place?
        "email-loe",       # previously recommended for removal — has a business case?
        "sharepoint",      # previously recommended for removal — has a business case?
    ]

    # Capability surface map from AGENTS.md
    CAPABILITY_MAP = {
        "neo4j": ("Memory/Knowledge", "code graph + sourcebot, experiments tier"),
        "fleet-triage": ("Ops/Orchestration", "issue funnel, daily automation, decision engine"),
        "docker": ("Ops/Orchestration", "container runtime for ms01 services"),
        "stagehand": ("Browser Automation", "local headless Chrome, portal automation"),
        "hermes": ("Ops/Orchestration", "fleet orchestration, agent health monitoring"),
        "email-loe": ("Browser Automation", "Gmail integration, email parsing for appraisal pipeline"),
        "sharepoint": ("Browser Automation", "SharePoint access for appraisal document retrieval"),
    }

    print()
    print("=" * 100)
    print("  SURFACE PROBES — business case + signal + verdict")
    print("=" * 100)

    for surface in PROBES:
        tier = SURFACE_TIERS.get(surface, "unclassified")
        cap, role = CAPABILITY_MAP.get(surface, ("unknown", "unknown"))
        case = _business_case(surface, tier, cap)
        facts = sum(len(v) for v in collector.domains.get(surface, {}).values())

        # Gather signals
        divested = intent.is_divested(surface)
        invested = intent.is_invested(surface)
        deprecated = intent.is_deprecated(surface)
        deprioritized = intent.is_deprioritized(surface)
        trend = intent.trend(surface)
        fc = intent.fix_cost(surface)

        # Determine opinion — start with business case, then add signal context
        opinions = []

        # Business case always comes first
        if case["revenue"] == "direct":
            opinions.append(f"revenue-generating surface — every hour of downtime costs throughput")
        elif case["revenue"] == "indirect":
            opinions.append(f"enables {case['enables']} — not directly revenue-generating but the pipeline depends on it")
        elif case["revenue"] == "operational":
            opinions.append(f"operational infrastructure — keeps the fleet running")

        if case.get("signal_thin"):
            opinions.append(f"value understood from capability role ({case['enables']}) — "
                           f"memory.db has only {facts} facts because this surface operates without generating error traces. "
                           f"Low signal is expected, not a removal signal")

        # Signal-based opinions
        if divested:
            opinions.append("you explicitly decided to move away from this integration layer")
        if deprecated:
            target = intent.is_deprecated(surface) or "replacement"
            opinions.append(f"migration to {target} is in progress — finish it, don't fix the old thing")
        if invested:
            opinions.append("you are actively building on this — protect the investment")
        if deprioritized:
            opinions.append("errors are worked around but never fixed — this is ambient noise, not a crisis")
        if trend == "rising":
            opinions.append("problems are getting worse — address before it compounds")
        elif trend == "falling":
            opinions.append("problems are resolving themselves — monitor, don't intervene")

        # Tier-based opinion
        if tier == "core" and not divested:
            opinions.append("revenue-critical — every hour of downtime costs pipeline throughput")
        elif tier == "infra" and invested:
            opinions.append("infrastructure backbone with active investment — keep healthy")
        elif tier == "experimental" and not invested and not case.get("signal_thin"):
            opinions.append("was tested and didn't stick — simpler to remove than maintain")

        # Fix cost opinion
        if fc != float('inf') and fc > 15:
            opinions.append(f"expensive to fix ({fc:.0f}:1) — may be more cost-effective to replace than repair")
        elif fc != float('inf') and fc < 5:
            opinions.append(f"cheap to fix ({fc:.0f}:1) — low-hanging fruit")

        # Recommendation — business case protects against rash removal
        if surface == "fleet-triage":
            rec = "self-aware — 0 facts is a self-reporting gap, not a removal signal"
            direction = "↻ self"
        elif divested:
            rec = "complete the divestment"
            direction = "⬇ shrink"
        elif deprecated:
            rec = f"finish migration to {intent.is_deprecated(surface)}"
            direction = "→ migrate"
        elif invested and tier in ("core", "infra"):
            rec = "protect and extend"
            direction = "⬆ grow"
        elif case.get("signal_thin") and case.get("revenue") != "none":
            # Known business case explains thin signal — value is visible through capability role
            rec = "value known from capability role — thin signal is normal for this surface"
            direction = "✓ known value"
        elif deprioritized and not case.get("signal_thin"):
            rec = "stop tracking this surface"
            direction = "⬇ shrink"
        elif facts < 5 and not case.get("signal_thin"):
            rec = "audit for removal"
            direction = "⬇ shrink"
        else:
            rec = "maintain as-is"
            direction = "— stable"

        print(f"\n  {surface}  [{tier}]  {direction}")
        print(f"    Capability: {cap} — {role}")
        print(f"    Business case: enables {case['enables']} ({case['revenue']})")
        if case.get("depends_on"):
            print(f"    Depends on: {', '.join(case['depends_on'])}")
        print(f"    Facts: {facts}  |  Fix cost: {fc if fc != float('inf') else 'never resolved'}")
        if opinions:
            for o in opinions[:5]:
                print(f"    • {o}")
        print(f"    Verdict: {rec}")

    # Also probe the system itself — eating its own dogfood
    print(f"\n  This system (fleet-triage) feeds on:")
    print(f"    • {sum(collector.fact_counts.values())} facts from memory.db")
    print(f"    • {GitHubScanner.repo_count()} GitHub repos")
    print(f"    • {Neo4jScanner.available() and 'Neo4j code graph' or 'Neo4j (offline)'}")
    if OTELScanner.available():
        print(f"    • {OTELScanner.metrics_summary().get('container_count', 0)} OTEL containers")
    print(f"    Decisions: {len(intent.divested)} surfaces marked for divestment")
    print(f"    Migrations: {len(intent.deprecated_services)} in progress")
    print(f"    Direction: {len(intent.invested)} surfaces with active investment")


def _business_case(surface: str, tier: str, capability: str) -> dict:
    """Build a business case for a surface: what value does it produce, and can the system see it?"""
    KNOWN_CASES = {
        "stagehand": {"enables": "portal form population — appraisal revenue pipeline", "revenue": "direct", "depends_on": ["credential-grabber", "doppler"], "signal_thin": False},
        "sfrep": {"enables": "Appraise-It Pro COM integration — UAD report population", "revenue": "direct", "depends_on": ["stagehand"], "signal_thin": False},
        "hermes": {"enables": "fleet orchestration, agent health, session management", "revenue": "operational", "depends_on": ["doppler", "tailscale", "ssh"], "signal_thin": False},
        "doppler": {"enables": "secret management for all automations", "revenue": "operational", "depends_on": [], "signal_thin": False},
        "bitwarden": {"enables": "human-facing credential vault — portal passwords", "revenue": "operational", "depends_on": [], "signal_thin": False},
        "email-loe": {"enables": "Gmail integration — parsing appraisal addresses", "revenue": "indirect", "depends_on": ["n8n", "hermes"], "signal_thin": True},
        "sharepoint": {"enables": "SharePoint document retrieval for appraisal workfiles", "revenue": "indirect", "depends_on": [], "signal_thin": True},
        "neo4j": {"enables": "code knowledge graph — cross-repo search, dependency mapping", "revenue": "operational", "depends_on": ["sourcebot"], "signal_thin": False},
        "fleet-triage": {"enables": "automated issue detection, filing, and handler dispatch", "revenue": "operational", "depends_on": ["memory.db", "github"], "signal_thin": True},
        "docker": {"enables": "container runtime for ms01 services", "revenue": "operational", "depends_on": ["ms01"], "signal_thin": False},
        "ntreis": {"enables": "MLS comp data — appraisal comparable sales", "revenue": "direct", "depends_on": ["stagehand", "trestle"], "signal_thin": False},
        "taxnet": {"enables": "TaxNetUSA property tax records", "revenue": "direct", "depends_on": ["stagehand", "credential-grabber"], "signal_thin": False},
        "truetracts": {"enables": "TrueTracts property data — appraisal comparables", "revenue": "direct", "depends_on": ["stagehand"], "signal_thin": False},
        "windmill": {"enables": "workflow engine — evaluated and abandoned per AGENTS.md", "revenue": "none", "depends_on": [], "signal_thin": False},
        "n8n": {"enables": "workflow automation — scheduled tasks, email routing", "revenue": "operational", "depends_on": ["doppler"], "signal_thin": False},
    }
    return KNOWN_CASES.get(surface, {"enables": f"unclassified surface ({capability})", "revenue": "unknown", "depends_on": [], "signal_thin": tier == "unclassified"})


def _is_noise_subpattern(pat: str) -> bool:
    """Return True if this sub-pattern is a generic section header, not actionable."""
    p = pat.strip().lower()
    noise = {'status', 'update', 'sitrep', "here's the summary", "here is the summary",
             'summary', 'plan (as requested)', 'result', "what i did",
             'files changed + behavior changes', 'implemented now',
             'section a:', 'section b:', 'findings', 'triage board:', 'result so far:',
             'test results summary', 'here is the full summary', 'remediation checklist'}
    for n in noise:
        if p == n or p.startswith(n):
            return True
    return len(p) < 10


def _short_title(domain: str, pattern: str) -> str:
    """Derive a short issue title from the domain + best sub-pattern."""
    p = pattern.strip()
    p = re.sub(r'^\d+x\s*', '', p)
    p = re.sub(r'^error:\s*', '', p)
    p = re.sub(r'^\[BLOCKER from \w+\]\s*', '', p)
    p = re.sub(r'^impact:\s*', '', p)
    noise_patterns = [
        r'^Here.?\s*(?:is|was)\s*(?:the|a)\s*(?:summary|status|result)',
        r'^\[resolved\]', r'^Sitrep', r'^Status\s*$', r'^Update\s*$',
        r'^I.ll\s+investigate', r'^\d+\s+tests?\s+pass',
    ]
    for np in noise_patterns:
        if re.match(np, p, re.IGNORECASE):
            return domain
    if '->' in p:
        parts = p.split('->', 1)
        p = parts[-1].strip()
    p = re.sub(r'^[-—>\s]+', '', p)
    p = p[:100].strip().rstrip('.:;-')
    if not p or len(p) < 8:
        return domain
    return f"{domain} — {p}"


def _get_domain_citations(domain: str) -> dict:
    """Query memory.db for session IDs and sample facts for a domain."""
    try:
        db = sqlite3.connect(str(DB_PATH))
        # Session IDs that mention this domain
        sessions = db.execute(
            "SELECT DISTINCT json_extract(metadata, '$.session_id') as sid FROM facts "
            "WHERE status='live' AND LOWER(content) LIKE ? "
            "AND json_extract(metadata, '$.session_id') IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 5",
            (f"%{domain.lower().replace('-', '').replace('_', '')}%",)
        ).fetchall()
        session_ids = [s[0] for s in sessions if s[0]]

        # Sample facts
        facts = db.execute(
            "SELECT category, substr(content, 1, 200), created_at FROM facts "
            "WHERE status='live' AND LOWER(content) LIKE ? "
            "ORDER BY created_at DESC LIMIT 3",
            (f"%{domain.lower().replace('-', '').replace('_', '')}%",)
        ).fetchall()

        db.close()
        return {
            "session_ids": session_ids,
            "sample_facts": [{"category": f[0], "content": f[1], "date": f[2]} for f in facts],
        }
    except Exception:
        return {"session_ids": [], "sample_facts": []}


def _handler_class(recommendation: str, tier: str) -> tuple:
    """Map recommendation + tier to handler class and risk level."""
    mapping = {
        "FIX": ("fix", "medium"),
        "REMOVE": ("remove", "high" if tier == "core" else "medium"),
        "INVESTIGATE": ("investigate", "low"),
        "MIGRATE": ("migrate", "medium"),
        "CONSOLIDATE": ("consolidate", "medium"),
    }
    rec_upper = recommendation.upper()
    for key in mapping:
        if key in rec_upper:
            return mapping[key]
    return ("investigate", "low")


def _build_issue_body(issue: dict) -> str:
    """Build a handler-ready GitHub issue body with citations, approach, and verification."""
    domain = issue["domain"]
    tier = issue["tier"]
    rec = issue["recommendation"]
    payoff = issue["payoff"]
    subs = issue.get("sub_patterns", [])

    hclass, risk = _handler_class(rec, tier)

    lines = []
    lines.append(f"**Domain:** {domain} | **Tier:** {tier} | **Payoff:** {payoff:.1f}")
    lines.append(f"**Handler class:** {hclass} | **Risk:** {risk} | **Estimated time:** 5-10 min")
    lines.append("")

    # Intent
    intent_parts = []
    if issue.get("intent_divested"): intent_parts.append("divested (moving away)")
    if issue.get("is_deprecated"):
        target = issue.get("dep_target", "replacement")
        intent_parts.append(f"migrating to {target}")
    if issue.get("intent_invested"): intent_parts.append("actively invested")
    if issue.get("intent_deprioritized"): intent_parts.append("deprioritized (worked around)")
    if issue.get("intent_external_fix"): intent_parts.append("fixes happen externally")
    trend = issue.get("trend", "")
    if trend == "rising": intent_parts.append("errors increasing")
    elif trend == "falling": intent_parts.append("errors declining")
    if intent_parts:
        lines.append("## Intent")
        lines.append(". ".join(intent_parts) + ".")
        lines.append("")

    # Fix cost
    fc = issue.get("fix_cost", float('inf'))
    if fc != float('inf') and fc > 0:
        lines.append(f"**Fix cost:** {fc:.0f}:1 errors per resolution")
    elif not issue.get("intent_external_fix") and not issue.get("intent_divested"):
        lines.append("**Fix cost:** never resolved")

    # Problem
    lines.append("## Problem")
    if subs:
        for pat, cnt in subs[:3]:
            clean = _clean_pattern(pat)
            lines.append(f"- [{cnt}x] {clean}")
    elif issue.get("derived_goal"):
        lines.append(f"**Goal:** {issue['derived_goal']}")
    lines.append("")

    # Goal
    dg = issue.get("derived_goal", "")
    lines.append("## Action")
    action_desc = "research this surface"
    if rec == "FIX":
        action_desc = f"apply a bounded, reversible fix for {domain}"
    elif rec == "REMOVE":
        action_desc = f"verify {domain} is safe to remove, recommend removal or archival"
    elif rec == "INVESTIGATE":
        action_desc = f"research {domain} surface, determine if it should be kept or removed"
    elif rec == "MIGRATE":
        target = issue.get("dep_target", "replacement")
        action_desc = f"migrate {domain} to {target}"
    elif rec == "CONSOLIDATE":
        action_desc = f"research consolidation options, categorize into keep/remove/merge"
    lines.append(f"**{rec}** — {action_desc}")
    lines.append("")

    # Citations
    cit = _get_domain_citations(domain)
    lines.append("## Citations")
    if cit["session_ids"]:
        lines.append(f"**Session IDs:** {', '.join(cit['session_ids'][:5])}")
    if cit["sample_facts"]:
        lines.append("**Sample facts:**")
        for f in cit["sample_facts"][:3]:
            lines.append(f"- [{f['category']}] {f['content'][:120]}... ({f['date'][:10]})")
    lines.append(f"**Memory query:** `python C:\\Users\\lkmot\\.factory\\memory\\harvester.py search \"{domain}\"`")
    lines.append("")

    # Proposed approach
    lines.append("## Proposed approach")
    lines.append("1. Verify citations are still fresh: run the memory query above")
    if hclass == "investigate":
        lines.append(f"2. Search memory.db for {domain} usage patterns")
        lines.append(f"3. Determine last active session and what {domain} was used for")
        lines.append(f"4. Check AGENTS.md capability surface map for {domain}")
        lines.append("5. Recommend: REMOVE (dormant/experimental), ARCHIVE (cold, has value), or KEEP (active)")
    elif hclass == "fix":
        lines.append(f"2. Diagnose the root cause of {domain} failures")
        lines.append(f"3. Apply a bounded, reversible fix (prefer config change, probe tweak, or one-line code edit)")
        lines.append("4. Commit to a branch, NOT main. Create a PR.")
    elif hclass == "consolidate":
        lines.append(f"2. List all {domain} items that need consolidation")
        lines.append("3. Categorize each: CLEAN-REMOVE, KEEP, MERGE, UNARCHIVE")
        lines.append("4. Recommend next steps (do NOT execute destructive actions without approval)")
    elif hclass == "remove":
        lines.append(f"2. Verify {domain} has no active dependencies (check AGENTS.md skills, running services)")
        lines.append("3. Check if any other surface references it")
        lines.append("4. Recommend removal path (just delete references? archive repo? disable service?)")
        lines.append("5. Do NOT execute removal — recommendation only at this phase")
    lines.append("")

    # Verification
    lines.append("## Verification")
    if hclass == "investigate":
        lines.append(f"`python C:\\Users\\lkmot\\.factory\\scripts\\verify-done.py --task-type research --question \"What should be done with {domain}?\" --answer \"<your recommendation>\" --sources \"memory.db\"`")
    elif hclass in ("fix", "consolidate"):
        lines.append(f"`python C:\\Users\\lkmot\\.factory\\scripts\\verify-done.py --task-type code --repo-path C:\\Users\\lkmot\\.factory`")
    else:
        lines.append(f"`python C:\\Users\\lkmot\\.factory\\scripts\\verify-done.py --task-type file --file C:\\Users\\lkmot\\.factory\\scripts\\issue_funnel.py`")
    lines.append("")

    # Constraints
    lines.append("## Constraints")
    lines.append(f"- Handler class: {hclass}")
    lines.append(f"- Risk: {risk}")
    lines.append("- Do NOT touch Safety Rules (bid submission, mass email, production deploy, data deletion, DNS)")
    if hclass in ("investigate", "consolidate"):
        lines.append("- **Read-only research phase.** Do NOT modify files, delete repos, or change configs.")
        lines.append("- If recommendation requires destructive action, flag as human-decision.")
    elif hclass == "fix":
        lines.append("- Apply bounded, reversible fixes only. Commit to branch, create PR, do NOT push to main.")
        lines.append("- If fix requires infrastructure changes or service restarts, flag as human-decision.")
    elif hclass == "remove":
        lines.append("- **Do NOT delete anything.** Produce a removal plan for operator approval.")
    lines.append("- Time budget: 15 min. Step budget: 20 tool calls.")
    lines.append("- Mandatory: verify-done.py, skill effectiveness line, next improvement line, governance record.")
    lines.append("")

    # Source footer
    richness = issue.get("signal_richness", {})
    facts = 0
    if isinstance(richness, dict):
        facts = richness.get("total_signal_facts", 0)
    lines.append("---")
    lines.append(f"Filed from {facts} memory.db facts | domain: {domain} | payoff: {payoff:.1f}")

    return "\n".join(lines)


def _issue_label(issue: dict) -> str:
    """Return a GitHub label for the issue."""
    rec = issue["recommendation"].lower()
    return rec


def _show_pros_cons_fix(domain: str, tier: str, goals: list, intent):
    """Pros/cons of FIX action."""
    print(f"\n    Action: FIX the root cause")
    for g in goals[:2]:
        label = GoalInference.GOALS.get(g[0], {}).get("label", g[0])
        print(f"    Pro: supports {label} (criticality {g[1]:.2f})")
    if tier == "core":
        print(f"    Pro: {domain} is revenue-critical — every hour of downtime costs throughput")
    elif tier == "infra":
        print(f"    Pro: {domain} is operational infrastructure — if it fails, visibility degrades")
    if intent.is_invested(domain):
        print(f"    Pro: you are actively investing in {domain} — this fix compounds with ongoing work")
    print(f"    Con of inaction: problem will recur. "
          f"{'You are already working around it.' if intent.is_deprioritized(domain) else 'Error volume will grow.'}")


def _show_pros_cons_remove(domain: str, tier: str, goals: list, intent):
    """Pros/cons of REMOVE action."""
    print(f"\n    Action: REMOVE this surface")
    print(f"    Pro: eliminates {domain} as an ongoing maintenance burden")
    if tier == "experimental":
        print(f"    Pro: {domain} is experimental — it was tested, did not stick. Simpler to delete than maintain.")
    elif intent.is_divested(domain):
        print(f"    Pro: you already decided to move away from {domain} — complete the divestment")
    print(f"    Con of inaction: {domain} continues to produce noise and consume attention")


def _show_pros_cons_migrate(domain: str, target: str, goals: list):
    """Pros/cons of MIGRATE action."""
    print(f"\n    Action: COMPLETE THE MIGRATION to {target}")
    print(f"    Pro: removes {domain} as a dependency — {target} is already provisioned")
    print(f"    Pro: migration unblocks revenue-continuity (no more token expiry outages)")
    print(f"    Con of inaction: {domain} failures will continue to cascade into dependent workflows")


def _show_pros_cons_investigate(domain: str, tier: str, goals: list):
    """Pros/cons of INVESTIGATE action."""
    print(f"\n    Action: INVESTIGATE before deciding")
    print(f"    Pro: avoids acting on incomplete signal — gather more data first")
    if tier == "core":
        print(f"    Pro: {domain} is core — worth the investigation before committing to a fix direction")
    print(f"    Con of inaction: unresolved issue may escalate or hide a deeper problem")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", action="store_true", help="File issues to GitHub instead of printing")
    parser.add_argument("--repo", default="lkmotto/fleet-triage", help="Target repo (default: lkmotto/fleet-triage)")
    args = parser.parse_args()

    if args.file:
        # Run funnel and file all issues
        import os
        if 'GH_TOKEN' not in os.environ:
            try:
                result = subprocess.run(
                    ['doppler', 'secrets', 'get', 'GITHUB_PAT', '--plain',
                     '--project', 'auth-sso', '--config', 'prd'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    os.environ['GH_TOKEN'] = result.stdout.strip()
            except Exception:
                print("ERROR: Could not get GH_TOKEN from Doppler. Set GH_TOKEN env var.")
                sys.exit(1)

        # Silence print output during collection — we only want the issues list
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        all_issues_data = run_funnel()
        sys.stdout = old_stdout

        filed = 0
        for issue in all_issues_data:
            body = _build_issue_body(issue)
            title = issue.get("title", issue["domain"])[:200]
            label = _issue_label(issue)
            rec = issue["recommendation"].lower()
            try:
                r = subprocess.run(
                    ['gh', 'issue', 'create', '--repo', args.repo,
                     '--title', title, '--body', body, '--label', rec],
                    capture_output=True, text=True, timeout=15
                )
                if r.returncode == 0:
                    filed += 1
                    print(f"  #{filed}: {title[:100]}")
                else:
                    print(f"  FAIL: {title[:80]} — {r.stderr.strip()[:100]}")
            except Exception as e:
                print(f"  ERROR: {title[:80]} — {e}")

        print(f"\nFiled {filed} issues to {args.repo}")
    else:
        run_funnel()


