# SPDX-License-Identifier: MIT
"""Unit tests for FastMCP tools exposed in server.py."""

from __future__ import annotations

import json
from unittest.mock import patch
import pytest

from core_web_vitals_mcp.server import (
    audit_pagespeed,
    check_for_updates,
    doctor,
    get_crux_history,
    get_crux_metrics,
    skill_read,
    skills_list,
)
from tests.conftest import (
    create_mock_crux_history_payload,
    create_mock_crux_payload,
    create_mock_pagespeed_payload,
)


@patch("core_web_vitals_mcp.client.WebVitalsClient._execute_http")
def test_get_crux_metrics_tool(mock_http):
    mock_http.return_value = create_mock_crux_payload("https://surendranb.com")
    res_str = get_crux_metrics("https://surendranb.com", form_factor="PHONE")

    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["core_web_vitals_assessment"] == "PASSED"
    assert "lcp" in data["metrics"]


def test_get_crux_metrics_empty_url():
    res = get_crux_metrics("")
    assert "[INPUT_FIXABLE]" in res


@patch("core_web_vitals_mcp.client.WebVitalsClient._execute_http")
def test_get_crux_history_tool(mock_http):
    mock_http.return_value = create_mock_crux_history_payload("https://surendranb.com")
    res_str = get_crux_history("https://surendranb.com")

    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["collection_periods_count"] == 4
    assert "inp" in data["metrics"]


@patch("core_web_vitals_mcp.client.WebVitalsClient._execute_http")
def test_audit_pagespeed_tool(mock_http):
    mock_http.return_value = create_mock_pagespeed_payload("https://surendranb.com", strategy="mobile")
    res_str = audit_pagespeed("https://surendranb.com", strategy="mobile")

    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["performance_score"] == 94
    assert "largest_contentful_paint" in data["lab_metrics"]


@patch("urllib.request.urlopen")
def test_doctor_healthy(mock_urlopen):
    # Mock reachable endpoints
    mock_resp = mock_urlopen.return_value.__enter__.return_value
    mock_resp.status = 200

    res_str = doctor(api_key="AIzaSyValidApiKey123456789")
    data = json.loads(res_str.split("\n\n[NOTICE")[0])

    assert data["status"] == "HEALTHY"
    assert data["credentials"]["configured"] is True
    assert "AIza...6789" in data["credentials"]["preview"]
    assert "crux_query" in data["endpoints"]
    assert len(data["available_skills"]) >= 3


def test_doctor_action_required(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("CRUX_API_KEY", raising=False)

    res_str = doctor(api_key=None)
    data = json.loads(res_str.split("\n\n[NOTICE")[0])

    assert data["status"] == "ACTION_REQUIRED"
    assert data["credentials"]["configured"] is False
    assert "[ENVIRONMENT_FIXABLE: STOP & ASK HUMAN]" in data["guidance"]


def test_skills_tools():
    list_res = skills_list()
    data = json.loads(list_res)
    assert len(data["skills"]) >= 3

    read_res = skill_read("lcp-optimization")
    assert "# Largest Contentful Paint" in read_res

    read_bad = skill_read("nonexistent-skill")
    assert "[INPUT_FIXABLE]" in read_bad


@patch("urllib.request.urlopen")
def test_check_for_updates(mock_urlopen):
    mock_resp = mock_urlopen.return_value.__enter__.return_value
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"info": {"version": "0.2.0"}}'

    res_str = check_for_updates(force=True)
    data = json.loads(res_str)
    assert data["package"] == "core-web-vitals-mcp"
    assert data["latest_version"] == "0.2.0"
    assert data["is_outdated"] is True
    assert "uvx --upgrade" in data["upgrade_command"]
