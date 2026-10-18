# SPDX-License-Identifier: MIT
"""Deterministic test fixtures covering Surendran's actual properties and test beds."""

from __future__ import annotations

import json
from typing import Any, Dict
import pytest

TEST_DOMAINS = [
    "surendranb.com",
    "freeinference.dev",
    "builditwithai.xyz",
    "ga4mcp.com",
]


def create_mock_crux_payload(url_or_origin: str, form_factor: str = "ALL_FORM_FACTORS") -> Dict[str, Any]:
    """Generate deterministic CrUX API queryRecord payload."""
    # Custom values per domain
    if "surendranb.com" in url_or_origin:
        lcp = 1450
        inp = 85
        cls = "0.02"
        fcp = 850
        ttfb = 210
    elif "freeinference.dev" in url_or_origin:
        lcp = 1850
        inp = 110
        cls = "0.04"
        fcp = 920
        ttfb = 280
    elif "builditwithai.xyz" in url_or_origin:
        lcp = 2100
        inp = 140
        cls = "0.06"
        fcp = 1100
        ttfb = 350
    else:  # ga4mcp.com or generic
        lcp = 1600
        inp = 95
        cls = "0.01"
        fcp = 780
        ttfb = 190

    return {
        "record": {
            "key": {
                "origin": url_or_origin if "/" not in url_or_origin.split("://")[-1] else None,
                "url": url_or_origin if "/" in url_or_origin.split("://")[-1] else None,
                "formFactor": form_factor,
            },
            "metrics": {
                "largest_contentful_paint": {
                    "histogram": [
                        {"start": 0, "end": 2500, "density": 0.88},
                        {"start": 2500, "end": 4000, "density": 0.08},
                        {"start": 4000, "density": 0.04},
                    ],
                    "percentiles": {"p75": lcp},
                },
                "interaction_to_next_paint": {
                    "histogram": [
                        {"start": 0, "end": 200, "density": 0.92},
                        {"start": 200, "end": 500, "density": 0.06},
                        {"start": 500, "density": 0.02},
                    ],
                    "percentiles": {"p75": inp},
                },
                "cumulative_layout_shift": {
                    "histogram": [
                        {"start": "0.00", "end": "0.10", "density": 0.95},
                        {"start": "0.10", "end": "0.25", "density": 0.03},
                        {"start": "0.25", "density": 0.02},
                    ],
                    "percentiles": {"p75": cls},
                },
                "first_contentful_paint": {
                    "histogram": [
                        {"start": 0, "end": 1800, "density": 0.90},
                        {"start": 1800, "end": 3000, "density": 0.07},
                        {"start": 3000, "density": 0.03},
                    ],
                    "percentiles": {"p75": fcp},
                },
                "experimental_time_to_first_byte": {
                    "histogram": [
                        {"start": 0, "end": 800, "density": 0.93},
                        {"start": 800, "end": 1800, "density": 0.05},
                        {"start": 1800, "density": 0.02},
                    ],
                    "percentiles": {"p75": ttfb},
                },
            },
            "collectionPeriod": {
                "firstDate": {"year": 2026, "month": 9, "day": 15},
                "lastDate": {"year": 2026, "month": 10, "day": 12},
            },
        }
    }


def create_mock_crux_history_payload(url_or_origin: str) -> Dict[str, Any]:
    """Generate deterministic CrUX History payload."""
    periods = [
        {
            "firstDate": {"year": 2026, "month": 5, "day": i * 7 + 1},
            "lastDate": {"year": 2026, "month": 5, "day": i * 7 + 28},
        }
        for i in range(4)
    ]
    return {
        "record": {
            "key": {"origin": url_or_origin},
            "collectionPeriods": periods,
            "metrics": {
                "largest_contentful_paint": {
                    "percentilesTimeseries": {"p75s": [1650, 1600, 1550, 1480]},
                },
                "interaction_to_next_paint": {
                    "percentilesTimeseries": {"p75s": [120, 110, 105, 95]},
                },
                "cumulative_layout_shift": {
                    "percentilesTimeseries": {"p75s": ["0.03", "0.03", "0.02", "0.02"]},
                },
                "first_contentful_paint": {
                    "percentilesTimeseries": {"p75s": [950, 920, 900, 870]},
                },
                "experimental_time_to_first_byte": {
                    "percentilesTimeseries": {"p75s": [260, 250, 240, 220]},
                },
            },
        }
    }


def create_mock_pagespeed_payload(url: str, strategy: str = "mobile") -> Dict[str, Any]:
    """Generate deterministic PageSpeed Insights payload."""
    score = 0.98 if strategy == "desktop" else 0.94
    return {
        "lighthouseResult": {
            "requestedUrl": url,
            "finalUrl": url,
            "categories": {
                "performance": {
                    "id": "performance",
                    "title": "Performance",
                    "score": score,
                }
            },
            "audits": {
                "first-contentful-paint": {
                    "id": "first-contentful-paint",
                    "title": "First Contentful Paint",
                    "score": 0.98,
                    "displayValue": "0.9 s",
                    "numericValue": 920.0,
                },
                "speed-index": {
                    "id": "speed-index",
                    "title": "Speed Index",
                    "score": 0.95,
                    "displayValue": "1.2 s",
                    "numericValue": 1240.0,
                },
                "largest-contentful-paint": {
                    "id": "largest-contentful-paint",
                    "title": "Largest Contentful Paint",
                    "score": 0.96,
                    "displayValue": "1.5 s",
                    "numericValue": 1490.0,
                },
                "total-blocking-time": {
                    "id": "total-blocking-time",
                    "title": "Total Blocking Time",
                    "score": 0.99,
                    "displayValue": "40 ms",
                    "numericValue": 40.0,
                },
                "cumulative-layout-shift": {
                    "id": "cumulative-layout-shift",
                    "title": "Cumulative Layout Shift",
                    "score": 1.0,
                    "displayValue": "0.01",
                    "numericValue": 0.01,
                },
                "interactive": {
                    "id": "interactive",
                    "title": "Time to Interactive",
                    "score": 0.96,
                    "displayValue": "1.4 s",
                    "numericValue": 1420.0,
                },
                "render-blocking-resources": {
                    "id": "render-blocking-resources",
                    "title": "Eliminate render-blocking resources",
                    "score": 0.75,
                    "displayValue": "Potential savings of 150 ms",
                    "details": {
                        "type": "opportunity",
                        "overallSavingsMs": 150,
                        "overallSavingsBytes": 24000,
                    },
                },
                "modern-image-formats": {
                    "id": "modern-image-formats",
                    "title": "Serve images in next-gen formats",
                    "score": 0.82,
                    "displayValue": "Potential savings of 80 KiB",
                    "details": {
                        "type": "opportunity",
                        "overallSavingsMs": 80,
                        "overallSavingsBytes": 81920,
                    },
                },
            },
        }
    }


@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch, tmp_path):
    """Ensure every test runs in clean isolation with telemetry disabled and cache cleared."""
    from core_web_vitals_mcp.client import clear_cache
    clear_cache()
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    monkeypatch.setenv("DISABLE_TELEMETRY", "1")
    monkeypatch.setenv("CORE_WEB_VITALS_TELEMETRY", "false")
    monkeypatch.setenv("GOOGLE_API_KEY", "mock-google-api-key-test-123456")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    yield tmp_path
    clear_cache()
