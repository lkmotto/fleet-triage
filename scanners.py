"""External data scanners: GitHub, Neo4j, OTEL/Prometheus.

These collect signal from external surfaces and produce issue dicts.
Separated from the decision engine (issue_funnel.py) so the funnel
focuses on intent, scoring, and ranking.
"""
import json, os, subprocess
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════
# GITHUB SCANNER — open issues, stale PRs, CI failures, repo metadata
# ═══════════════════════════════════════════════════════════════════

class GitHubScanner:
    """Query GitHub for open issues, stale PRs, CI failures, and repo metadata."""

    _ci_cache = None  # cached CI failures across ALL lkmotto repos

    @staticmethod
    def _gh(*args) -> list | None:
        """Run gh CLI with auth from Doppler."""
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
                pass
        try:
            r = subprocess.run(['gh'] + list(args), capture_output=True, text=True, timeout=15)
            if r.returncode != 0:
                return None
            return json.loads(r.stdout)
        except Exception:
            return None

    @classmethod
    def _all_repos(cls) -> list[str]:
        """Fetch ALL non-archived lkmotto repos. Cached for the run."""
        if not hasattr(cls, '_repo_cache'):
            r = cls._gh('repo', 'list', 'lkmotto', '--limit=200',
                        '--no-archived', '--json=name')
            cls._repo_cache = [repo['name'] for repo in (r or [])]
        return cls._repo_cache

    @classmethod
    def _active_repos(cls) -> list[str]:
        """Repos with recent pushes (last 30 days) — worth checking CI for."""
        r = cls._gh('repo', 'list', 'lkmotto', '--limit=200',
                    '--no-archived', '--json=name,pushedAt')
        active = []
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()[:10]
        for repo in (r or []):
            pushed = (repo.get('pushedAt', '') or '')[:10]
            if pushed >= cutoff:
                active.append(repo['name'])
        return active

    @classmethod
    def _all_ci_failures(cls) -> list[dict]:
        """Fetch CI failures across active lkmotto repos. Cached."""
        if cls._ci_cache is not None:
            return cls._ci_cache
        cls._ci_cache = []
        active = cls._active_repos()
        for repo in active:
            r = cls._gh('run', 'list', '-R', f'lkmotto/{repo}',
                        '--status=failure', '--limit=1',
                        '--json=name,conclusion,createdAt,headBranch')
            if r:
                for run in r:
                    cls._ci_cache.append({
                        "repo": repo,
                        "name": run.get('name', '?')[:60],
                        "branch": run.get('headBranch', '?'),
                        "date": run.get('createdAt', '?')[:10],
                    })
        return cls._ci_cache

    @staticmethod
    def scan(domain: str) -> dict:
        """Return GitHub context for a domain."""
        ctx = {"issues": 0, "duplicates": [], "ci_failures": [], "stale_prs": 0,
               "total_repos_scan": len(GitHubScanner._all_repos())}

        r = GitHubScanner._gh('search', 'issues',
            f'"{domain}" owner:lkmotto state:open', '--limit=5',
            '--json=title,url,repository')
        if r:
            ctx["issues"] = len(r)
            for issue in r:
                repo_name = issue.get('repository', {}).get('nameWithOwner', '?')
                if domain.lower() in issue.get('title', '').lower():
                    ctx["duplicates"].append({
                        "title": issue.get('title', '')[:80],
                        "repo": repo_name,
                        "url": issue.get('url', ''),
                    })

        domain_clean = domain.lower().replace('-', '').replace('_', '')
        all_failures = GitHubScanner._all_ci_failures()
        for cf in all_failures:
            if domain_clean in cf['repo'].lower().replace('-', '').replace('_', ''):
                ctx["ci_failures"].append(cf)

        return ctx

    @classmethod
    def global_ci_summary(cls) -> list[dict]:
        """Return ALL CI failures across all repos (for standalone issues)."""
        return cls._all_ci_failures()

    @classmethod
    def repo_count(cls) -> int:
        return len(cls._all_repos())


# ═══════════════════════════════════════════════════════════════════
# NEO4J SCANNER — code graph health across indexed repos
# ═══════════════════════════════════════════════════════════════════

class Neo4jScanner:
    """Query neo4j code graph for repo staleness, archival status, pipeline health."""

    NEO4J_URL = "http://192.168.1.120:7474/db/neo4j/tx/commit"
    NEO4J_AUTH = "neo4j:Ic856BqACb9UVXaKO3WEQNrS1xRTmYoi"

    @staticmethod
    def available() -> bool:
        try:
            result = subprocess.run(
                ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code}",
                 "http://192.168.1.120:7474"],
                capture_output=True, text=True, timeout=3
            )
            return result.stdout.strip() == "200"
        except Exception:
            return False

    @staticmethod
    def _query(cypher: str) -> list:
        try:
            result = subprocess.run(
                ["curl.exe", "-s", "-u", Neo4jScanner.NEO4J_AUTH,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps({"statements": [{"statement": cypher}]}),
                 Neo4jScanner.NEO4J_URL],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return []
            data = json.loads(result.stdout)
            if "errors" in data and data["errors"]:
                return []
            return data.get("results", [{}])[0].get("data", [])
        except Exception:
            return []

    @staticmethod
    def repo_issues() -> list[dict]:
        """Return issues derived from neo4j code graph analysis."""
        issues = []

        if not Neo4jScanner.available():
            return issues

        # Archived repos
        rows = Neo4jScanner._query(
            "MATCH (r:Repository) WHERE r.isArchived = true RETURN r.name, r.lastPush"
        )
        if rows:
            names = [r["row"][0].split("/")[-1] if "/" in str(r["row"][0]) else str(r["row"][0])
                     for r in rows[:5]]
            issues.append({
                "domain": "archived-repos",
                "tier": "infra",
                "recommendation": "CONSOLIDATE",
                "confidence": "high",
                "score": 0.9,
                "payoff": 6.0,
                "goal": "surface-hygiene",
                "goal_criticality": 0.5,
                "signal_richness": {"dimensions": {"neo4j": 1}, "total_signal_facts": len(rows)},
                "sub_patterns": [(f"{len(rows)} archived repos in code graph: {', '.join(names[:3])}...", len(rows))],
                "rationale": f"{len(rows)} archived repos still indexed — should be removed from code graph",
                "narrative": "",
                "engine_dep": False,
                "github": {},
            })

        # Stale repos (no push in 90+ days)
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        rows = Neo4jScanner._query(
            f"MATCH (r:Repository) WHERE r.lastPush IS NOT NULL AND r.lastPush < '{cutoff}' "
            "AND r.isArchived = false RETURN r.name, r.lastPush ORDER BY r.lastPush ASC LIMIT 10"
        )
        if rows:
            names = [f"{r['row'][0].split('/')[-1]} ({r['row'][1]})" if len(r["row"]) > 1 else str(r["row"][0])
                     for r in rows[:5]]
            issues.append({
                "domain": "stale-repos",
                "tier": "infra",
                "recommendation": "INVESTIGATE",
                "confidence": "high",
                "score": 0.85,
                "payoff": 5.5,
                "goal": "surface-hygiene",
                "goal_criticality": 0.5,
                "signal_richness": {"dimensions": {"neo4j": 1}, "total_signal_facts": len(rows)},
                "sub_patterns": [(f"{len(rows)} repos with no push in 90+ days: {', '.join(names[:3])}...", len(rows))],
                "rationale": f"{len(rows)} repos untouched for 90+ days — audit for archival",
                "narrative": "",
                "engine_dep": False,
                "github": {},
            })

        # Code graph health summary
        stats = Neo4jScanner._query(
            "MATCH (r:Repository) RETURN count(r) as total, "
            "count(CASE WHEN r.isArchived THEN 1 END) as archived, "
            "count(CASE WHEN r.isPrivate THEN 1 END) as private"
        )
        if stats and stats[0].get("row"):
            total, archived, private = stats[0]["row"]
            issues.append({
                "domain": "code-graph-health",
                "tier": "infra",
                "recommendation": "FIX",
                "confidence": "medium",
                "score": 0.7,
                "payoff": 4.0,
                "goal": "infra-health",
                "goal_criticality": 0.7,
                "signal_richness": {"dimensions": {"neo4j": 1}, "total_signal_facts": total},
                "sub_patterns": [(f"{total} repos indexed, {archived} archived ({archived*100//total if total else 0}%), {private} private", 1)],
                "rationale": f"{archived}/{total} repos archived — {archived*100//total if total else 0}% archival rate is high",
                "narrative": "",
                "engine_dep": False,
                "github": {},
            })

        return issues


# ═══════════════════════════════════════════════════════════════════
# OTEL SCANNER — Prometheus metrics for container/network health
# ═══════════════════════════════════════════════════════════════════

class OTELScanner:
    """Query Prometheus (via Grafana proxy) for container resource anomalies.

    Detects: high CPU (>200% or >500%), high memory (>75% or >90% of limit),
    restarts, network errors.
    """

    PROMETHEUS_URL = (
        "http://192.168.1.120:3000/api/datasources/proxy/uid/prometheus/api/v1"
    )
    GRAFANA_AUTH = "admin:admin"

    CPU_WARN = 2.0
    CPU_CRITICAL = 5.0
    MEM_WARN = 0.75
    MEM_CRITICAL = 0.90

    @staticmethod
    def available() -> bool:
        try:
            result = subprocess.run(
                ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code}",
                 "-u", OTELScanner.GRAFANA_AUTH,
                 "http://192.168.1.120:3000/api/health"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "200"
        except Exception:
            return False

    @staticmethod
    def _query(query: str) -> dict:
        import urllib.request
        url = (f"{OTELScanner.PROMETHEUS_URL}/query?query="
               + urllib.request.quote(query))
        try:
            result = subprocess.run(
                ["curl.exe", "-s", "-u", OTELScanner.GRAFANA_AUTH, url],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0 or not result.stdout.strip():
                return {}
            return json.loads(result.stdout)
        except Exception:
            return {}

    @staticmethod
    def container_issues() -> list[dict]:
        """Return issues derived from OTEL container metrics."""
        issues = []

        if not OTELScanner.available():
            return issues

        # CPU anomalies
        cpu_data = OTELScanner._query(
            'avg by (container_name) (rate(container_cpu_usage_nanoseconds_total[5m]) / 1e9)'
        )
        for res in cpu_data.get("data", {}).get("result", []):
            name = res["metric"].get("container_name", "?")
            val = float(res["value"][1])
            cores = val
            if cores > OTELScanner.CPU_CRITICAL:
                issues.append({
                    "domain": f"container-{name}",
                    "tier": "infra",
                    "recommendation": "FIX",
                    "confidence": "high",
                    "score": 0.95,
                    "payoff": 8.0,
                    "goal": "infra-health",
                    "goal_criticality": 0.7,
                    "signal_richness": {"dimensions": {"otel": 1}, "total_signal_facts": 1},
                    "sub_patterns": [(f"CRITICAL: {name} using {cores:.1f} cores CPU", 1)],
                    "rationale": f"{name} at {cores:.1f} cores CPU — above {OTELScanner.CPU_CRITICAL:.0f}-core threshold",
                    "narrative": "",
                    "engine_dep": False,
                    "github": {},
                })
            elif cores > OTELScanner.CPU_WARN:
                issues.append({
                    "domain": f"container-{name}",
                    "tier": "infra",
                    "recommendation": "INVESTIGATE",
                    "confidence": "medium",
                    "score": 0.7,
                    "payoff": 4.5,
                    "goal": "infra-health",
                    "goal_criticality": 0.7,
                    "signal_richness": {"dimensions": {"otel": 1}, "total_signal_facts": 1},
                    "sub_patterns": [(f"WARN: {name} using {cores:.1f} cores CPU", 1)],
                    "rationale": f"{name} at {cores:.1f} cores CPU — above {OTELScanner.CPU_WARN:.0f}-core threshold",
                    "narrative": "",
                    "engine_dep": False,
                    "github": {},
                })

        # Memory anomalies
        mem_data = OTELScanner._query(
            'avg by (container_name) ('
            'container_memory_usage_total_bytes / '
            'container_memory_usage_limit_bytes'
            ')'
        )
        for res in mem_data.get("data", {}).get("result", []):
            name = res["metric"].get("container_name", "?")
            val = float(res["value"][1])
            if val > OTELScanner.MEM_CRITICAL:
                issues.append({
                    "domain": f"container-{name}",
                    "tier": "infra",
                    "recommendation": "FIX",
                    "confidence": "high",
                    "score": 0.9,
                    "payoff": 7.0,
                    "goal": "infra-health",
                    "goal_criticality": 0.7,
                    "signal_richness": {"dimensions": {"otel": 1}, "total_signal_facts": 1},
                    "sub_patterns": [(f"CRITICAL: {name} memory at {val*100:.0f}%", 1)],
                    "rationale": f"{name} memory at {val*100:.0f}% of limit — add memory or fix leak",
                    "narrative": "",
                    "engine_dep": False,
                    "github": {},
                })
            elif val > OTELScanner.MEM_WARN:
                issues.append({
                    "domain": f"container-{name}",
                    "tier": "infra",
                    "recommendation": "INVESTIGATE",
                    "confidence": "medium",
                    "score": 0.65,
                    "payoff": 4.0,
                    "goal": "infra-health",
                    "goal_criticality": 0.7,
                    "signal_richness": {"dimensions": {"otel": 1}, "total_signal_facts": 1},
                    "sub_patterns": [(f"WARN: {name} memory at {val*100:.0f}%", 1)],
                    "rationale": f"{name} memory at {val*100:.0f}% of limit — monitor for memory leak",
                    "narrative": "",
                    "engine_dep": False,
                    "github": {},
                })

        # Network errors (dropped packets)
        net_data = OTELScanner._query(
            'avg by (container_name) ('
            'rate(container_network_io_usage_rx_dropped_total[5m]) + '
            'rate(container_network_io_usage_tx_dropped_total[5m])'
            ')'
        )
        for res in net_data.get("data", {}).get("result", []):
            name = res["metric"].get("container_name", "?")
            val = float(res["value"][1])
            if val > 0:
                issues.append({
                    "domain": f"container-{name}",
                    "tier": "infra",
                    "recommendation": "INVESTIGATE",
                    "confidence": "low",
                    "score": 0.4,
                    "payoff": 2.5,
                    "goal": "infra-health",
                    "goal_criticality": 0.7,
                    "signal_richness": {"dimensions": {"otel": 1}, "total_signal_facts": 1},
                    "sub_patterns": [(f"Network drops: {name} at {val:.2f} packets/sec dropped", 1)],
                    "rationale": f"{name} has {val:.2f} dropped packets/sec — check network config",
                    "narrative": "",
                    "engine_dep": False,
                    "github": {},
                })

        return issues

    @staticmethod
    def metrics_summary() -> dict:
        """Return a dashboard summary: container count, total metrics, top consumers."""
        if not OTELScanner.available():
            return {"available": False}

        total_metrics = OTELScanner._query('count({__name__=~".+"})')
        container_metrics = OTELScanner._query('count({__name__=~"container_.*"})')

        top_cpu = OTELScanner._query(
            'topk(5, avg by (container_name) (rate(container_cpu_usage_nanoseconds_total[5m]) / 1e9))'
        )

        summary = {
            "available": True,
            "total_metrics": 0,
            "container_metrics": 0,
            "top_cpu": [],
            "container_count": 0,
        }

        if total_metrics.get("data", {}).get("result"):
            summary["total_metrics"] = int(total_metrics["data"]["result"][0]["value"][1])

        if container_metrics.get("data", {}).get("result"):
            summary["container_metrics"] = int(container_metrics["data"]["result"][0]["value"][1])

        if top_cpu.get("data", {}).get("result"):
            for res in top_cpu["data"]["result"]:
                name = res["metric"].get("container_name", "?")
                val = float(res["value"][1])
                summary["top_cpu"].append((name, round(val, 2)))

        cnt_data = OTELScanner._query(
            'count(count by (container_name) (container_cpu_usage_nanoseconds_total))'
        )
        if cnt_data.get("data", {}).get("result"):
            summary["container_count"] = int(cnt_data["data"]["result"][0]["value"][1])

        return summary
