"""Deterministic parser for API documentation (Markdown, OpenAPI JSON, YAML)."""

from __future__ import annotations

import json
import re
from typing import Any

from app.modules.importer.schemas import CandidateMonitor
from app.modules.importer.ssrf import is_safe_url
from app.modules.monitors.models import HttpMethod

_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

# Regex for Markdown headers e.g.:
# ### `GET /api/v1/monitors`
# ## POST /api/v1/auth/signup
_MD_HEADER_PATTERN = re.compile(
    r"^(?:#{1,6})\s+[`'\"]?(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)[`'\"]?\s+[`'\"]?([^\s`'\"]+)[`'\"]?",
    re.IGNORECASE | re.MULTILINE,
)

# Regex for Markdown tables e.g.:
# | GET | /api/v1/monitors | 200 |
_MD_TABLE_PATTERN = re.compile(
    r"\|\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*\|\s*([^\|]+?)\s*(?:\|\s*(\d{3})\s*)?\|",
    re.IGNORECASE,
)

# Regex to detect expected status code in surrounding text
_STATUS_CODE_PATTERN = re.compile(
    r"(?:response|returns|status|expect(?:ed)?)\s*(?:\(|:)?\s*[`'\"]?(\d{3})",
    re.IGNORECASE,
)


def parse_api_documentation(
    content: str,
    filename: str,
    default_base_url: str | None = None,
) -> list[CandidateMonitor]:
    """Extract candidate monitors from uploaded API documentation content."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".json"):
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "paths" in data:
                return _parse_openapi_dict(data, default_base_url)
        except Exception:
            pass  # Fallback to text/markdown scanning

    if filename_lower.endswith((".yaml", ".yml")):
        # Simple YAML paths detection if PyYAML is available, or fallback
        try:
            import yaml  # type: ignore[import-untyped]

            data = yaml.safe_load(content)
            if isinstance(data, dict) and "paths" in data:
                return _parse_openapi_dict(data, default_base_url)
        except Exception:
            pass

    return _parse_markdown(content, default_base_url)


def _parse_openapi_dict(
    data: dict[str, Any], default_base_url: str | None
) -> list[CandidateMonitor]:
    candidates: list[CandidateMonitor] = []
    base_url = default_base_url or ""
    servers = data.get("servers", [])
    if not base_url and servers and isinstance(servers, list):
        first_server = servers[0]
        if isinstance(first_server, dict):
            base_url = first_server.get("url", "")

    paths: dict[str, Any] = data.get("paths", {})
    for path, methods_dict in paths.items():
        if not isinstance(methods_dict, dict):
            continue
        for method_str, op_dict in methods_dict.items():
            method_upper = method_str.upper()
            if method_upper not in _VALID_METHODS:
                continue

            summary = (
                op_dict.get("summary") or op_dict.get("operationId") or f"{method_upper} {path}"
            )
            expected_status = 200
            responses = op_dict.get("responses", {})
            if isinstance(responses, dict):
                for code_str in responses.keys():
                    if code_str.isdigit() and code_str.startswith("2"):
                        expected_status = int(code_str)
                        break

            full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}" if base_url else path
            is_safe, error = is_safe_url(full_url, allow_relative=True)

            candidates.append(
                CandidateMonitor(
                    name=summary[:150],
                    url=full_url,
                    method=HttpMethod(method_upper),
                    expected_status_code=expected_status,
                    description=op_dict.get("description"),
                    is_valid=is_safe,
                    validation_error=error,
                )
            )

    return candidates


def _parse_markdown(content: str, default_base_url: str | None) -> list[CandidateMonitor]:
    candidates: list[CandidateMonitor] = []
    seen: set[tuple[str, str]] = set()
    base_url = (default_base_url or "").rstrip("/")

    # 1. Parse header-based endpoints e.g. ### GET /api/v1/monitors
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        match = _MD_HEADER_PATTERN.match(line.strip())
        if match:
            method_str = match.group(1).upper()
            path_str = match.group(2).strip()
            key = (method_str, path_str)
            if key in seen:
                continue
            seen.add(key)

            # Look ahead in next 10 lines for status code or description
            expected_code = 201 if method_str == "POST" else 200
            description = None
            for lookahead_idx in range(idx + 1, min(idx + 15, len(lines))):
                sub_line = lines[lookahead_idx].strip()
                if sub_line.startswith("#"):
                    break  # Hit next section
                code_match = _STATUS_CODE_PATTERN.search(sub_line)
                if code_match:
                    try:
                        code_val = int(code_match.group(1))
                        if 100 <= code_val <= 599:
                            expected_code = code_val
                    except ValueError:
                        pass
                if not description and sub_line and not sub_line.startswith("```"):
                    description = sub_line[:150]

            full_url = (
                f"{base_url}/{path_str.lstrip('/')}"
                if base_url and path_str.startswith("/")
                else path_str
            )
            is_safe, error = is_safe_url(full_url, allow_relative=True)

            candidates.append(
                CandidateMonitor(
                    name=f"{method_str} {path_str}"[:150],
                    url=full_url,
                    method=HttpMethod(method_str),
                    expected_status_code=expected_code,
                    description=description,
                    is_valid=is_safe,
                    validation_error=error,
                )
            )

    # 2. Parse table-based endpoints e.g. | GET | /api/v1/monitors | 200 |
    for line in lines:
        table_match = _MD_TABLE_PATTERN.search(line)
        if table_match:
            method_str = table_match.group(1).upper()
            path_str = table_match.group(2).strip().strip("`").strip()
            # Skip header divider rows like |---|---|
            if not path_str or path_str.startswith("-") or "/" not in path_str:
                continue

            key = (method_str, path_str)
            if key in seen:
                continue
            seen.add(key)

            code_str = table_match.group(3)
            expected_code = (
                int(code_str)
                if code_str and code_str.isdigit()
                else (201 if method_str == "POST" else 200)
            )

            full_url = (
                f"{base_url}/{path_str.lstrip('/')}"
                if base_url and path_str.startswith("/")
                else path_str
            )
            is_safe, error = is_safe_url(full_url, allow_relative=True)

            candidates.append(
                CandidateMonitor(
                    name=f"{method_str} {path_str}"[:150],
                    url=full_url,
                    method=HttpMethod(method_str),
                    expected_status_code=expected_code,
                    is_valid=is_safe,
                    validation_error=error,
                )
            )

    return candidates
