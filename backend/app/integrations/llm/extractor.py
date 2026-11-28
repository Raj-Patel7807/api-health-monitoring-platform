"""LLM-powered API markdown extractor using Gemini Flash Lite."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.modules.monitors.schemas import HttpMethod

logger = logging.getLogger(__name__)

GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)


class ExtractedEndpoint(BaseModel):
    name: str = Field(..., description="Descriptive name of the endpoint")
    method: HttpMethod = Field(default=HttpMethod.GET, description="HTTP method")
    url: str = Field(..., description="Full target URL")
    expected_status_code: int = Field(default=200, ge=100, le=599)
    timeout_seconds: int = Field(default=10, gt=0, le=300)
    check_interval_seconds: int = Field(default=60, gt=0, le=86400)
    failure_threshold: int = Field(default=3, gt=0, le=100)
    recovery_threshold: int = Field(default=2, gt=0, le=100)
    description: str | None = None


class ExtractionResult(BaseModel):
    endpoints: list[ExtractedEndpoint] = []
    total_found: int = 0
    warnings: list[str] = []
    used_llm: bool = False


def _preprocess_markdown(content: str, max_chars: int = 24000) -> str:
    """Strip unnecessary markdown bulk to minimize Gemini token usage."""
    # Remove image links
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", content)
    # Remove large code blocks with non-JSON content or long dummy payloads
    cleaned = re.sub(r"```(?!json)[a-zA-Z]*\n[\s\S]*?```", "", cleaned)
    # Remove excessive whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned[:max_chars].strip()


def _resolve_url(raw_path_or_url: str, base_url: str | None) -> str:
    """Combine base_url and relative path or sanitize raw URL."""
    cleaned = raw_path_or_url.strip()
    if cleaned.startswith(("http://", "https://")):
        return cleaned

    # Path parameter replacement: /users/{id} -> /users/1 for basic health checking
    cleaned = re.sub(r"\{[a-zA-Z0-9_]+\}", "1", cleaned)
    cleaned = re.sub(r":([a-zA-Z0-9_]+)", "1", cleaned)

    if base_url:
        normalized_base = base_url.rstrip("/")
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned
        return f"{normalized_base}{cleaned}"

    # Default fallback host if neither is absolute
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return f"http://localhost:8000{cleaned}"


def _heuristic_extract(markdown_content: str, base_url: str | None) -> list[ExtractedEndpoint]:
    """Fallback rule-based regex extraction when LLM is unconfigured or unreachable."""
    endpoints: list[ExtractedEndpoint] = []
    seen: set[tuple[str, str]] = set()

    # Pattern matches headings or lines like:
    # ### `POST /auth/login` or `GET /api/v1/monitors`
    pattern = re.compile(
        r"(?:###?\s*`?|\b)(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([/a-zA-Z0-9_\-.:{}]+)`?",
        re.IGNORECASE,
    )

    lines = markdown_content.splitlines()
    for idx, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            method_str = match.group(1).upper()
            path_str = match.group(2).strip()

            try:
                method = HttpMethod(method_str)
            except ValueError:
                continue

            full_url = _resolve_url(path_str, base_url)
            pair = (method.value, full_url)
            if pair in seen:
                continue
            seen.add(pair)

            # Look ahead for status codes like 201 Response or 200 OK
            expected_status = 200
            window = "\n".join(lines[idx : idx + 8])
            status_match = re.search(r"\b(200|201|202|204)\b", window)
            if status_match:
                expected_status = int(status_match.group(1))

            # Generate friendly name
            name_parts = [
                p.capitalize()
                for p in path_str.strip("/").split("/")
                if p and not p.startswith(("{", ":"))
            ]
            name = f"{method.value} {' '.join(name_parts) if name_parts else 'Root'}"

            endpoints.append(
                ExtractedEndpoint(
                    name=name[:150],
                    method=method,
                    url=full_url,
                    expected_status_code=expected_status,
                )
            )

    return endpoints


async def extract_endpoints_from_markdown(
    markdown_content: str,
    base_url: str | None = None,
) -> ExtractionResult:
    """Extract API endpoints from markdown using Gemini Flash Lite with heuristic fallback."""
    settings = get_settings()
    warnings: list[str] = []

    if not markdown_content.strip():
        return ExtractionResult(
            endpoints=[], total_found=0, warnings=["Markdown content is empty."]
        )

    # If Gemini API key is missing, immediately use heuristic parser
    if not settings.gemini_api_key.strip():
        warnings.append(
            "GEMINI_API_KEY is not configured in .env. "
            "Extracted endpoints using the heuristic parser."
        )
        endpoints = _heuristic_extract(markdown_content, base_url)
        return ExtractionResult(
            endpoints=endpoints,
            total_found=len(endpoints),
            warnings=warnings,
            used_llm=False,
        )

    # Use Gemini Flash Lite
    cleaned_doc = _preprocess_markdown(markdown_content)
    system_instruction = (
        "You are an expert API specification extractor. "
        "Analyze the provided API documentation and extract all HTTP endpoints. "
        "For each endpoint, return a JSON object with: "
        "- name: short descriptive name (e.g. 'User Login') "
        "- method: HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) "
        "- path: route path or full URL (e.g. '/api/v1/auth/login') "
        "- expected_status_code: successful HTTP status code (200, 201, 204, etc. Default 200) "
        "- description: one-sentence summary if available. "
        "Return ONLY a JSON array of objects. Do not wrap with prose or commentary."
    )

    prompt = f"API Documentation:\n```markdown\n{cleaned_doc}\n```\nExtract all endpoints:"

    payload: dict[str, Any] = {
        "contents": [
            {
                "parts": [
                    {"text": system_instruction},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }

    model_name = settings.gemini_model.strip() or "gemini-2.0-flash-lite"
    url = GEMINI_API_URL_TEMPLATE.format(model=model_name, key=settings.gemini_api_key)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code != 200:
                logger.warning(
                    "Gemini API returned status %s: %s. Falling back to heuristic.",
                    response.status_code,
                    response.text[:200],
                )
                warnings.append(
                    f"Gemini API responded with HTTP {response.status_code}. "
                    "Fallback heuristic extractor applied."
                )
                endpoints = _heuristic_extract(markdown_content, base_url)
                return ExtractionResult(
                    endpoints=endpoints,
                    total_found=len(endpoints),
                    warnings=warnings,
                    used_llm=False,
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                warnings.append("Gemini returned no candidates. Falling back to heuristic.")
                endpoints = _heuristic_extract(markdown_content, base_url)
                return ExtractionResult(
                    endpoints=endpoints,
                    total_found=len(endpoints),
                    warnings=warnings,
                    used_llm=False,
                )

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "[]")
            parsed_items = json.loads(raw_text)

            extracted: list[ExtractedEndpoint] = []
            seen_pairs: set[tuple[str, str]] = set()

            for item in parsed_items:
                raw_path = str(item.get("path") or item.get("url") or "").strip()
                if not raw_path:
                    continue

                method_str = str(item.get("method", "GET")).strip().upper()
                try:
                    method = HttpMethod(method_str)
                except ValueError:
                    method = HttpMethod.GET

                resolved_url = _resolve_url(raw_path, base_url)
                pair = (method.value, resolved_url)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                status_code = int(item.get("expected_status_code") or 200)
                name = str(item.get("name") or f"{method.value} {raw_path}")[:150]

                extracted.append(
                    ExtractedEndpoint(
                        name=name,
                        method=method,
                        url=resolved_url,
                        expected_status_code=status_code,
                        description=item.get("description"),
                    )
                )

            return ExtractionResult(
                endpoints=extracted,
                total_found=len(extracted),
                warnings=warnings,
                used_llm=True,
            )

    except Exception as exc:
        logger.exception("Error calling Gemini API: %s", exc)
        warnings.append(
            f"AI extraction encountered an error: {exc}. Heuristic parser used as fallback."
        )
        endpoints = _heuristic_extract(markdown_content, base_url)
        return ExtractionResult(
            endpoints=endpoints,
            total_found=len(endpoints),
            warnings=warnings,
            used_llm=False,
        )
