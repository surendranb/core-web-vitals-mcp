# SPDX-License-Identifier: MIT
"""Unit tests for WebVitalsClient and metric processing."""

from __future__ import annotations

import urllib.error
import pytest
from unittest.mock import MagicMock, patch

from core_web_vitals_mcp.client import (
    WebVitalsClient,
    extract_crux_metrics,
    normalize_target,
    rate_metric,
    resolve_api_key,
)
from tests.conftest import (
    TEST_DOMAINS,
    create_mock_crux_history_payload,
    create_mock_crux_payload,
    create_mock_pagespeed_payload,
)


def test_normalize_target():
    origin, is_origin = normalize_target("surendranb.com")
    assert origin == "https://surendranb.com"
    assert is_origin is True

    origin2, is_origin2 = normalize_target("https://surendranb.com/")
    assert origin2 == "https://surendranb.com"
    assert is_origin2 is True

    url, is_origin3 = normalize_target("https://surendranb.com/blog/article-1")
    assert url == "https://surendranb.com/blog/article-1"
    assert is_origin3 is False

    with pytest.raises(ValueError) as excinfo:
        normalize_target("   ")
    assert "[INPUT_FIXABLE]" in str(excinfo.value)


def test_rate_metric():
    assert rate_metric("largest_contentful_paint", 1500) == "GOOD"
    assert rate_metric("largest_contentful_paint", 3000) == "NEEDS_IMPROVEMENT"
    assert rate_metric("largest_contentful_paint", 4500) == "POOR"

    assert rate_metric("interaction_to_next_paint", 150) == "GOOD"
    assert rate_metric("interaction_to_next_paint", 300) == "NEEDS_IMPROVEMENT"
    assert rate_metric("interaction_to_next_paint", 600) == "POOR"

    assert rate_metric("cumulative_layout_shift", 0.05) == "GOOD"
    assert rate_metric("cumulative_layout_shift", 0.18) == "NEEDS_IMPROVEMENT"
    assert rate_metric("cumulative_layout_shift", 0.35) == "POOR"


def test_resolve_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("CRUX_API_KEY", raising=False)

    val, src = resolve_api_key(None)
    assert val is None
    assert src == "none"

    val, src = resolve_api_key("param-key")
    assert val == "param-key"
    assert src == "parameter"

    monkeypatch.setenv("CRUX_API_KEY", "env-crux-key")
    val, src = resolve_api_key(None)
    assert val == "env-crux-key"
    assert "CRUX_API_KEY" in src


def test_extract_crux_metrics_good():
    mock_payload = create_mock_crux_payload("https://surendranb.com")
    parsed = extract_crux_metrics(mock_payload["record"])

    assert parsed["core_web_vitals_assessment"] == "PASSED"
    metrics = parsed["metrics"]
    assert "lcp" in metrics
    assert "inp" in metrics
    assert "cls" in metrics
    assert metrics["lcp"]["rating"] == "GOOD"
    assert metrics["inp"]["rating"] == "GOOD"
    assert metrics["cls"]["rating"] == "GOOD"
    assert metrics["lcp"]["histogram"]["good_pct"] == 88.0


def test_extract_crux_metrics_failed():
    record = {
        "key": {"origin": "https://poor-site.com"},
        "metrics": {
            "largest_contentful_paint": {"percentiles": {"p75": 5200}},
            "interaction_to_next_paint": {"percentiles": {"p75": 100}},
            "cumulative_layout_shift": {"percentiles": {"p75": 0.02}},
        },
    }
    parsed = extract_crux_metrics(record)
    assert parsed["core_web_vitals_assessment"] == "FAILED"
    assert parsed["metrics"]["lcp"]["rating"] == "POOR"


@patch.object(WebVitalsClient, "_execute_http")
def test_query_crux_record_all_test_beds(mock_http):
    client = WebVitalsClient(api_key="test-key")

    for domain in TEST_DOMAINS:
        url = f"https://{domain}"
        mock_http.return_value = create_mock_crux_payload(url)
        res = client.query_crux_record(url)
        assert res["core_web_vitals_assessment"] == "PASSED"
        assert res["metrics"]["lcp"]["p75"] > 0
        assert res["metrics"]["inp"]["p75"] > 0


@patch.object(WebVitalsClient, "_execute_http")
def test_query_crux_history(mock_http):
    client = WebVitalsClient(api_key="test-key")
    mock_http.return_value = create_mock_crux_history_payload("https://surendranb.com")

    res = client.query_crux_history("https://surendranb.com")
    assert res["collection_periods_count"] == 4
    assert "lcp" in res["metrics"]
    assert len(res["metrics"]["lcp"]["p75_timeseries"]) == 4


@patch.object(WebVitalsClient, "_execute_http")
def test_run_pagespeed_audit(mock_http):
    client = WebVitalsClient(api_key="test-key")
    mock_http.return_value = create_mock_pagespeed_payload("https://surendranb.com", strategy="mobile")

    res = client.run_pagespeed_audit("https://surendranb.com", strategy="mobile")
    assert res["performance_score"] == 94
    assert res["strategy"] == "mobile"
    assert res["lab_metrics"]["largest_contentful_paint"]["numericValue"] == 1490.0
    assert len(res["top_opportunities"]) > 0


@patch("urllib.request.urlopen")
def test_error_absorption_404(mock_urlopen):
    err = urllib.error.HTTPError(
        url="https://chromeuxreport.googleapis.com",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=MagicMock(read=lambda: b'{"error": {"message": "record not found"}}'),
    )
    mock_urlopen.side_effect = err

    client = WebVitalsClient()
    with pytest.raises(FileNotFoundError) as excinfo:
        client._execute_http("https://chromeuxreport.googleapis.com")
    assert "[INPUT_FIXABLE]" in str(excinfo.value)
    assert "No CrUX field record found" in str(excinfo.value)


@patch("urllib.request.urlopen")
def test_error_absorption_403(mock_urlopen):
    err = urllib.error.HTTPError(
        url="https://chromeuxreport.googleapis.com",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=MagicMock(read=lambda: b'{"error": {"message": "API key not valid"}}'),
    )
    mock_urlopen.side_effect = err

    client = WebVitalsClient()
    with pytest.raises(PermissionError) as excinfo:
        client._execute_http("https://chromeuxreport.googleapis.com")
    assert "[ENVIRONMENT_FIXABLE: STOP & ASK HUMAN]" in str(excinfo.value)
    assert "Google Cloud Console" in str(excinfo.value)


@patch("urllib.request.urlopen")
def test_error_absorption_429(mock_urlopen):
    err = urllib.error.HTTPError(
        url="https://chromeuxreport.googleapis.com",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=MagicMock(read=lambda: b'{"error": {"message": "Rate limit exceeded"}}'),
    )
    mock_urlopen.side_effect = err

    client = WebVitalsClient()
    with pytest.raises(RuntimeError) as excinfo:
        client._execute_http("https://chromeuxreport.googleapis.com")
    assert "[TRANSIENT]" in str(excinfo.value)
    assert "rate limit exceeded" in str(excinfo.value)


@patch("urllib.request.urlopen")
def test_error_absorption_network_timeout(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("timed out")

    client = WebVitalsClient()
    with pytest.raises(ConnectionError) as excinfo:
        client._execute_http("https://chromeuxreport.googleapis.com")
    assert "[TRANSIENT]" in str(excinfo.value)
    assert "Failed to connect to Google APIs" in str(excinfo.value)


@patch.object(WebVitalsClient, "_execute_http")
def test_keyless_mode_crux_fallback(mock_http, monkeypatch):
    """When no API key is provided, CrUX should gracefully fall back to PageSpeed lab audit."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("CRUX_API_KEY", raising=False)
    mock_http.return_value = create_mock_pagespeed_payload("https://surendranb.com")

    client = WebVitalsClient(api_key=None)
    res = client.query_crux_record("https://surendranb.com")

    assert res["status"] == "FIELD_DATA_REQUIRES_KEY"
    assert res["has_crux_data"] is False
    assert "google-api-setup" in res["system_directive"]
    assert res["performance_score"] == 94
    assert "largest_contentful_paint" in res["lab_metrics"]


@patch.object(WebVitalsClient, "_execute_http")
def test_crux_404_zero_traffic_graceful_handling(mock_http):
    """When CrUX returns 404 (not enough Chrome user data), absorb as NO_FIELD_DATA and provide lab fallback."""
    # First call (CrUX) raises 404, second call (PageSpeed fallback) succeeds
    err_404 = FileNotFoundError("[INPUT_FIXABLE] No CrUX field record found.")
    mock_pagespeed = create_mock_pagespeed_payload("https://low-traffic.com")
    mock_http.side_effect = [err_404, mock_pagespeed]

    client = WebVitalsClient(api_key="valid-test-key")
    res = client.query_crux_record("https://low-traffic.com")

    assert res["status"] == "NO_FIELD_DATA"
    assert res["has_crux_data"] is False
    assert "not have sufficient real-user Chrome traffic" in res["message"]
    assert res["performance_score"] == 94


def test_japanese_idn_and_path_encoding():
    """Verify Japanese IDN domains (.jp) and non-ASCII paths are properly normalized."""
    origin, is_origin = normalize_target("https://総務省.jp")
    assert origin == "https://xn--lhr645fjve.jp"
    assert is_origin is True

    url, is_origin_url = normalize_target("https://yahoo.co.jp/ニュース/記事")
    assert is_origin_url is False
    assert "%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9" in url


def test_numeric_input_coercion():
    """Verify numeric/integer inputs from fuzzers don't crash with AttributeError."""
    origin, is_origin = normalize_target(12345)
    assert "https://12345" in origin


@patch.object(WebVitalsClient, "_execute_http")
def test_rate_limiter_and_caching(mock_http):
    """Verify in-memory caching returns identical results without duplicate network requests."""
    mock_http.return_value = create_mock_pagespeed_payload("https://cache-test.com")

    client = WebVitalsClient(api_key="test-key")
    res1 = client.run_pagespeed_audit("https://cache-test.com")
    res2 = client.run_pagespeed_audit("https://cache-test.com")

    assert res1 == res2
    assert mock_http.call_count == 1  # Cache hit on 2nd call
