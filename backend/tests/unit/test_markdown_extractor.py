"""Unit tests for the Agentic AI markdown extractor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.llm.extractor import (
    _heuristic_extract,
    _preprocess_markdown,
    _resolve_url,
    extract_endpoints_from_markdown,
)
from app.modules.monitors.schemas import HttpMethod


def test_preprocess_markdown_strips_images_and_non_json_code():
    raw_md = (
        "# Title\n\n"
        "![Diagram](https://example.com/arch.png)\n\n"
        "```python\ndef foo():\n    return 42\n```\n\n"
        "### `GET /api/v1/health`\n"
    )
    processed = _preprocess_markdown(raw_md)
    assert "![Diagram]" not in processed
    assert "def foo():" not in processed
    assert "GET /api/v1/health" in processed


def test_resolve_url():
    # Relative path with base_url
    assert (
        _resolve_url("/api/v1/users", "https://api.acme.com") == "https://api.acme.com/api/v1/users"
    )
    # Relative path without leading slash
    assert _resolve_url("health", "https://api.acme.com") == "https://api.acme.com/health"
    # Path parameter replacement
    assert (
        _resolve_url("/api/v1/monitors/{id}", "https://api.acme.com")
        == "https://api.acme.com/api/v1/monitors/1"
    )
    # Absolute URL remains unchanged
    assert (
        _resolve_url("https://status.other.com/ping", "https://api.acme.com")
        == "https://status.other.com/ping"
    )


def test_heuristic_extract_finds_endpoints():
    sample_doc = """
    # Service Endpoints

    ### `POST /auth/login`
    Logs in the user.
    Status: 200 OK

    ### `GET /health`
    Liveness check.
    Returns 200 OK.

    ### `POST /users`
    Create user.
    201 Created.
    """
    endpoints = _heuristic_extract(sample_doc, "https://api.example.com")
    assert len(endpoints) == 3

    methods = {e.method for e in endpoints}
    assert HttpMethod.POST in methods
    assert HttpMethod.GET in methods

    urls = {e.url for e in endpoints}
    assert "https://api.example.com/auth/login" in urls
    assert "https://api.example.com/health" in urls
    assert "https://api.example.com/users" in urls

    post_user = next(e for e in endpoints if e.url == "https://api.example.com/users")
    assert post_user.expected_status_code == 201


@pytest.mark.asyncio
async def test_extract_endpoints_no_key_falls_back_heuristic():
    with patch("app.integrations.llm.extractor.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = ""
        mock_settings.return_value.gemini_model = "gemini-2.0-flash-lite"

        result = await extract_endpoints_from_markdown(
            "### `GET /api/v1/ping`",
            base_url="https://test.com",
        )
        assert result.used_llm is False
        assert len(result.endpoints) == 1
        assert result.endpoints[0].url == "https://test.com/api/v1/ping"
        assert result.endpoints[0].method == HttpMethod.GET
        assert any("GEMINI_API_KEY is not configured" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_extract_endpoints_with_gemini_mocked():
    with patch("app.integrations.llm.extractor.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "fake-key"
        mock_settings.return_value.gemini_model = "gemini-2.0-flash-lite"

        gemini_response_json = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '[{"name": "Auth Login", "method": "POST", "path": '
                                    '"/auth/login", "expected_status_code": 200, '
                                    '"description": "Login route"}]'
                                )
                            }
                        ]
                    }
                }
            ]
        }

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = gemini_response_json

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_http_response
        ):
            result = await extract_endpoints_from_markdown(
                "# API\nPOST /auth/login",
                base_url="https://myservice.io",
            )
            assert result.used_llm is True
            assert len(result.endpoints) == 1
            assert result.endpoints[0].name == "Auth Login"
            assert result.endpoints[0].method == HttpMethod.POST
            assert result.endpoints[0].url == "https://myservice.io/auth/login"
            assert result.endpoints[0].expected_status_code == 200
