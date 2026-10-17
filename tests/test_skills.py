# SPDX-License-Identifier: MIT
"""Unit tests for dynamic skills layer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from core_web_vitals_mcp.skills import (
    list_available_skills,
    read_skill_content,
    skill_read,
    skills_list,
)


def test_list_available_skills():
    skills = list_available_skills()
    assert "lcp-optimization" in skills
    assert "inp-debugging" in skills
    assert "cls-remediation" in skills


def test_read_bundled_skills_local_fallback():
    for skill_name in ("lcp-optimization", "inp-debugging", "cls-remediation"):
        content, success = read_skill_content(skill_name)
        assert success is True
        assert len(content) > 100
        assert "# " in content


@patch("urllib.request.urlopen")
def test_remote_fetch_priority(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"# Remote Live Skill Content"
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    content, success = read_skill_content("lcp-optimization")
    assert success is True
    assert content == "# Remote Live Skill Content"


def test_unknown_skill():
    content, success = read_skill_content("nonexistent-skill-abc")
    assert success is False
    assert "[INPUT_FIXABLE]" in content
    assert "Unknown skill 'nonexistent-skill-abc'" in content


def test_empty_skill():
    content, success = read_skill_content("   ")
    assert success is False
    assert "[INPUT_FIXABLE]" in content
