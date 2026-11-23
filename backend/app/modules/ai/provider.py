"""AI incident assistance provider abstraction and implementations."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class IncidentAnalysisContext:
    incident_id: str
    monitor_name: str
    monitor_url: str
    failure_count: int
    http_status_code: int | None
    response_time_ms: int | None
    error_message: str | None
    is_timeout: bool
    is_connection_error: bool
    is_ssl_error: bool
    recent_errors: list[str] = field(default_factory=list)


@dataclass
class IncidentAnalysisResult:
    summary: str
    root_cause: str
    suggested_actions: list[str]
    investigation_steps: list[str]
    prevention_steps: list[str]
    model: str


class BaseAIProvider(ABC):
    """Abstract base class for incident analysis providers."""

    @abstractmethod
    def analyze(self, context: IncidentAnalysisContext) -> IncidentAnalysisResult:
        """Analyze the incident context and return an explanatory diagnosis."""
        raise NotImplementedError


class DeterministicRuleAIProvider(BaseAIProvider):
    """High-reliability deterministic rule-based analysis engine.

    Never fails due to external API outages, zero external dependencies,
    and adheres to all domain rules for API incident diagnosis.
    """

    def analyze(self, context: IncidentAnalysisContext) -> IncidentAnalysisResult:
        name = context.monitor_name
        code = context.http_status_code
        err = context.error_message or "Unknown failure"

        if context.is_timeout:
            return IncidentAnalysisResult(
                summary=(
                    f"Monitor '{name}' timed out repeatedly. The target endpoint failed to "
                    f"respond within the configured timeout threshold."
                ),
                root_cause=(
                    "Network saturation, unoptimized backend database queries, deadlock, "
                    "or upstream service latency preventing response generation."
                ),
                suggested_actions=[
                    "Check target server CPU, memory, and database connection pool utilization.",
                    "Review slow query logs on the database backing this endpoint.",
                    "Verify upstream network latency and gateway timeouts.",
                    "Temporarily scale replica instances if under high traffic.",
                ],
                investigation_steps=[
                    f"Check server metrics around timeout event ({context.response_time_ms}ms).",
                    "Check reverse proxy access logs for 504 / 499 statuses.",
                    "Profile the endpoint execution path with APM or distributed tracing.",
                ],
                prevention_steps=[
                    "Implement query pagination, database indexing, and caching.",
                    "Configure graceful circuit breaking on downstream dependencies.",
                    "Set up proactive alerts for response time degradation before timeouts occur.",
                ],
                model="deterministic-rules",
            )

        if context.is_ssl_error:
            return IncidentAnalysisResult(
                summary=(
                    f"SSL/TLS handshake failure detected for '{name}'. Clients cannot securely "
                    f"negotiate an encrypted connection."
                ),
                root_cause=(
                    "Expired TLS certificate, untrusted certificate authority, "
                    "mismatched SNI hostname, or unsupported cipher suite."
                ),
                suggested_actions=[
                    "Inspect the SSL/TLS certificate validity dates and renewal status.",
                    "Verify automated certificate renewal jobs (e.g. Let's Encrypt / Certbot).",
                    "Ensure intermediate CA certificates are properly bundled on the server.",
                ],
                investigation_steps=[
                    "Run openssl s_client to inspect certificate chain validity.",
                    "Verify domain DNS to confirm traffic reaches the intended server.",
                ],
                prevention_steps=[
                    "Enable automated certificate renewal monitoring 30 days prior to expiry.",
                    "Use managed certificates via Cloudflare, ACM, or Let's Encrypt.",
                ],
                model="deterministic-rules",
            )

        if context.is_connection_error:
            return IncidentAnalysisResult(
                summary=(
                    f"Connection refused or network unreachable for '{name}'. "
                    f"The monitoring engine could not establish a TCP connection."
                ),
                root_cause=(
                    "Target web service process is down, DNS resolution failed, "
                    "or firewall/security group rules are dropping inbound probe traffic."
                ),
                suggested_actions=[
                    "Check if the web server process (Uvicorn, Gunicorn, Node.js) is running.",
                    "Inspect systemd service status or container orchestration (Docker/K8s).",
                    "Verify firewall, security groups, and ingress routing rules.",
                ],
                investigation_steps=[
                    "Check container/host uptime and restart crash logs.",
                    "Verify DNS A/AAAA records for the target hostname.",
                    "Test TCP reachability using `curl -v` or `nc -zv` from an external probe.",
                ],
                prevention_steps=[
                    "Configure automated process supervisors (systemd, Docker restart policies).",
                    "Deploy redundant instances across multiple availability zones.",
                ],
                model="deterministic-rules",
            )

        if code is not None and 500 <= code <= 599:
            reason = (
                "Internal server error" if code == 500 else f"HTTP {code} Gateway / Service Error"
            )
            return IncidentAnalysisResult(
                summary=(
                    f"Target '{name}' returned HTTP {code} ({reason}) across "
                    f"{context.failure_count} consecutive checks."
                ),
                root_cause=(
                    f"Server-side unhandled exception, crashed worker process, or upstream gateway "
                    f"failure: {err}."
                ),
                suggested_actions=[
                    "Check application error logs for stack traces at failure time.",
                    "Verify that downstream databases, caches, and third-party APIs are reachable.",
                    "Restart affected application workers or rollback recent problematic releases.",
                ],
                investigation_steps=[
                    "Filter application logs by error level and search for unhandled exceptions.",
                    "Check database connection pool exhaustion and memory leaks.",
                    "Correlate failure onset with recent git releases or configuration changes.",
                ],
                prevention_steps=[
                    "Implement comprehensive exception handling and defensive fallbacks in code.",
                    "Use canary deployments and automated integration tests prior to release.",
                    "Add health check endpoints that verify essential internal dependencies.",
                ],
                model="deterministic-rules",
            )

        if code is not None and code in (401, 403):
            return IncidentAnalysisResult(
                summary=(
                    f"Authentication or permission denied (HTTP {code}) for monitor '{name}'. "
                    f"The probe request was rejected by the server."
                ),
                root_cause=(
                    "Expired API key, invalid bearer token, changed authorization rules, or IP "
                    "whitelisting blocking the health monitor."
                ),
                suggested_actions=[
                    "Verify the authorization headers or credentials configured for this monitor.",
                    "Ensure service accounts or API keys have not expired or been revoked.",
                    "Check server-side RBAC and IP access restriction policies.",
                ],
                investigation_steps=[
                    "Review authentication gateway / OAuth provider audit logs for denials.",
                    "Compare monitor request headers against target endpoint requirements.",
                ],
                prevention_steps=[
                    "Use long-lived monitoring credentials with minimal required read-only scopes.",
                    "Set up automated credential rotation warnings prior to expiration.",
                ],
                model="deterministic-rules",
            )

        if code is not None and code == 404:
            return IncidentAnalysisResult(
                summary=(
                    f"Endpoint not found (HTTP 404) for monitor '{name}'. "
                    f"The requested URL path does not exist on the server."
                ),
                root_cause=(
                    "Changed API route path, missing API prefix, or decommissioned endpoint."
                ),
                suggested_actions=[
                    "Check whether the API path has changed in a recent release.",
                    "Update the monitor URL to match the active health check endpoint.",
                ],
                investigation_steps=[
                    f"Verify route definitions in router for '{context.monitor_url}'.",
                    "Check API routing and ingress path rewrite rules.",
                ],
                prevention_steps=[
                    "Maintain backward-compatible API routing and deprecation periods.",
                    "Update monitoring configuration in sync with API route changes.",
                ],
                model="deterministic-rules",
            )

        # Default fallback analysis
        return IncidentAnalysisResult(
            summary=(
                f"Repeated health check failures detected for '{name}'. "
                f"Incident triggered after {context.failure_count} consecutive failing probes."
            ),
            root_cause=err,
            suggested_actions=[
                "Inspect the latest health check results and response payload in the dashboard.",
                "Verify service availability and responsiveness from outside the cluster.",
            ],
            investigation_steps=[
                "Check application and infrastructure logs corresponding to probe timestamps.",
                "Review recent commits and infrastructure changes around the incident start time.",
            ],
            prevention_steps=[
                "Implement end-to-end integration tests and automated monitoring alerts.",
                "Review failure threshold settings for sensitivity balance.",
            ],
            model="deterministic-rules",
        )


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini LLM provider with graceful fallback to deterministic rules."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self.fallback = DeterministicRuleAIProvider()

    def analyze(self, context: IncidentAnalysisContext) -> IncidentAnalysisResult:
        if not self.api_key:
            return self.fallback.analyze(context)

        prompt = (
            "You are an expert site reliability and backend engineer. Analyze this API incident "
            "and output a strict JSON object with these keys: 'summary', 'root_cause', "
            "'suggested_actions' (list of strings), 'investigation_steps' (list of strings), "
            "'prevention_steps' (list of strings).\n\n"
            f"Monitor Name: {context.monitor_name}\n"
            f"HTTP Status Code: {context.http_status_code}\n"
            f"Response Time Ms: {context.response_time_ms}\n"
            f"Error: {context.error_message}\n"
            f"Is Timeout: {context.is_timeout}\n"
            f"Is SSL Error: {context.is_ssl_error}\n"
            f"Is Connection Error: {context.is_connection_error}\n"
            f"Consecutive Failures: {context.failure_count}\n"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_content = candidates[0]["content"]["parts"][0]["text"]
                        parsed = json.loads(text_content)
                        return IncidentAnalysisResult(
                            summary=str(parsed.get("summary", "")),
                            root_cause=str(parsed.get("root_cause", "")),
                            suggested_actions=[str(x) for x in parsed.get("suggested_actions", [])],
                            investigation_steps=[
                                str(x) for x in parsed.get("investigation_steps", [])
                            ],
                            prevention_steps=[str(x) for x in parsed.get("prevention_steps", [])],
                            model=f"gemini-{self.model}",
                        )
        except Exception as exc:
            logger.warning("Gemini AI incident analysis failed (%s); falling back to rules.", exc)

        return self.fallback.analyze(context)


def get_ai_provider() -> BaseAIProvider:
    """Return configured AI analysis provider based on environment settings."""
    settings = get_settings()
    if settings.llm_enabled and settings.llm_provider.lower() == "gemini" and settings.llm_api_key:
        return GeminiAIProvider(api_key=settings.llm_api_key, model=settings.llm_model)
    return DeterministicRuleAIProvider()
