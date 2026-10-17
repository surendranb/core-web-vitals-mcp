# SPDX-License-Identifier: MIT
"""Client library for Google Chrome UX Report (CrUX) and PageSpeed Insights APIs."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

CRUX_QUERY_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
CRUX_HISTORY_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryHistoryRecord"
PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

VALID_FORM_FACTORS = {"ALL_FORM_FACTORS", "PHONE", "DESKTOP", "TABLET"}

# Metric thresholds (in ms except CLS which is a unitless score)
METRIC_THRESHOLDS = {
    "largest_contentful_paint": {"good": 2500, "poor": 4000, "unit": "ms"},
    "interaction_to_next_paint": {"good": 200, "poor": 500, "unit": "ms"},
    "cumulative_layout_shift": {"good": 0.10, "poor": 0.25, "unit": "score"},
    "first_contentful_paint": {"good": 1800, "poor": 3000, "unit": "ms"},
    "experimental_time_to_first_byte": {"good": 800, "poor": 1800, "unit": "ms"},
    "time_to_first_byte": {"good": 800, "poor": 1800, "unit": "ms"},
}

# Known test bed sites for deterministic fixtures and connectivity verification
TEST_BED_DOMAINS = [
    "surendranb.com",
    "freeinference.dev",
    "builditwithai.xyz",
    "ga4mcp.com",
]


def resolve_api_key(api_key: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Resolves Google API Key from arguments or environment variables.

    Returns:
        (key_value, key_source)
    """
    if api_key and api_key.strip():
        return api_key.strip(), "parameter"
    for env_var in (
        "CRUX_API_KEY",
        "GOOGLE_API_KEY",
        "PAGESPEED_API_KEY",
        "GOOGLE_CLOUD_API_KEY",
    ):
        val = os.environ.get(env_var)
        if val and val.strip():
            return val.strip(), f"environment ({env_var})"
    return None, "none"


def normalize_target(url_or_origin: str) -> Tuple[str, bool]:
    """Normalizes target string and determines if it is an origin or a URL.

    Returns:
        (normalized_string, is_origin)
    """
    target = url_or_origin.strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        target = f"https://{target}"

    parsed = urllib.parse.urlparse(target)
    if not parsed.netloc:
        raise ValueError(
            f"[INPUT_FIXABLE] Invalid URL or origin '{url_or_origin}'. "
            "Target must contain a valid domain name (e.g. 'https://surendranb.com')."
        )

    # If path is empty or just "/", treat as origin
    if (not parsed.path or parsed.path == "/") and not parsed.query:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return origin, True
    return target, False


def rate_metric(metric_name: str, p75_val: float) -> str:
    """Calculates GOOD, NEEDS_IMPROVEMENT, or POOR rating for a metric value."""
    key = metric_name.lower()
    threshold = METRIC_THRESHOLDS.get(key)
    if not threshold:
        return "UNKNOWN"
    if p75_val <= threshold["good"]:
        return "GOOD"
    if p75_val > threshold["poor"]:
        return "POOR"
    return "NEEDS_IMPROVEMENT"


def parse_density(density: Any) -> float:
    try:
        return round(float(density) * 100, 2)
    except (ValueError, TypeError):
        return 0.0


def extract_crux_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    """Parses raw CrUX record into human-friendly structured metrics."""
    metrics_data = record.get("metrics", {})
    key_info = record.get("key", {})
    collection_period = record.get("collectionPeriod", {})

    parsed_metrics: Dict[str, Any] = {}
    core_ratings: List[str] = []

    metric_mapping = {
        "largest_contentful_paint": "lcp",
        "interaction_to_next_paint": "inp",
        "cumulative_layout_shift": "cls",
        "first_contentful_paint": "fcp",
        "experimental_time_to_first_byte": "ttfb",
        "time_to_first_byte": "ttfb",
    }

    for raw_name, clean_name in metric_mapping.items():
        if raw_name in metrics_data:
            item = metrics_data[raw_name]
            p75 = item.get("percentiles", {}).get("p75")
            if p75 is not None:
                try:
                    p75_float = float(p75)
                except (ValueError, TypeError):
                    continue
                rating = rate_metric(raw_name, p75_float)
                if clean_name in ("lcp", "inp", "cls"):
                    core_ratings.append(rating)

                histogram = item.get("histogram", [])
                hist_summary = {}
                if len(histogram) >= 3:
                    hist_summary = {
                        "good_pct": parse_density(histogram[0].get("density")),
                        "needs_improvement_pct": parse_density(histogram[1].get("density")),
                        "poor_pct": parse_density(histogram[2].get("density")),
                    }

                unit = METRIC_THRESHOLDS.get(raw_name, {}).get("unit", "ms")
                parsed_metrics[clean_name] = {
                    "p75": p75_float,
                    "unit": unit,
                    "rating": rating,
                    "histogram": hist_summary,
                }

    # Core Web Vitals overall assessment
    if not core_ratings:
        assessment = "INSUFFICIENT_DATA"
    elif all(r == "GOOD" for r in core_ratings):
        assessment = "PASSED"
    elif any(r == "POOR" for r in core_ratings):
        assessment = "FAILED"
    else:
        assessment = "NEEDS_IMPROVEMENT"

    return {
        "target": key_info.get("url") or key_info.get("origin") or "unknown",
        "form_factor": key_info.get("formFactor", "ALL_FORM_FACTORS"),
        "collection_period": collection_period,
        "core_web_vitals_assessment": assessment,
        "metrics": parsed_metrics,
    }


class WebVitalsClient:
    """Client for CrUX and PageSpeed Insights APIs with error absorption and mock fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key, self.key_source = resolve_api_key(api_key)

    def _execute_http(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        req_headers = {"User-Agent": "core-web-vitals-mcp/0.1.0"}
        if headers:
            req_headers.update(headers)

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                resp_bytes = resp.read()
                return json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as http_err:
            code = http_err.code
            err_text = ""
            try:
                raw_err = http_err.read().decode("utf-8", "replace")
                err_json = json.loads(raw_err)
                err_text = err_json.get("error", {}).get("message", raw_err)
            except Exception:
                err_text = str(http_err)

            if code == 404 or "not found" in err_text.lower():
                raise FileNotFoundError(
                    f"[INPUT_FIXABLE] No CrUX field record found. Google Chrome UX Report requires sufficient "
                    "real-world user traffic over a 28-day rolling window. "
                    "Try querying the origin (e.g. 'https://example.com') or use audit_pagespeed() for synthetic lab testing."
                ) from http_err

            if code == 400:
                raise ValueError(
                    f"[INPUT_FIXABLE] Bad Request (HTTP 400): {err_text}"
                ) from http_err

            if code in (401, 403):
                raise PermissionError(
                    f"[ENVIRONMENT_FIXABLE: STOP & ASK HUMAN] Google Cloud API error (HTTP {code}): {err_text}\n"
                    "Guidance:\n"
                    "1. Go to Google Cloud Console: https://console.cloud.google.com/\n"
                    "2. Enable 'Chrome UX Report API' and 'PageSpeed Insights API'\n"
                    "3. Generate an API Key in APIs & Services -> Credentials\n"
                    "4. Set environment variable GOOGLE_API_KEY=<your-key> or CRUX_API_KEY=<your-key>"
                ) from http_err

            if code == 429:
                raise RuntimeError(
                    f"[TRANSIENT] Google API rate limit exceeded (HTTP 429): {err_text}. "
                    "Please wait a few moments before retrying."
                ) from http_err

            if code >= 500:
                raise RuntimeError(
                    f"[TRANSIENT] Google API internal server error (HTTP {code}): {err_text}. "
                    "The Google service is temporarily unavailable."
                ) from http_err

            raise RuntimeError(f"HTTP {code}: {err_text}") from http_err

        except urllib.error.URLError as url_err:
            raise ConnectionError(
                f"[TRANSIENT] Failed to connect to Google APIs ({url_err.reason}). "
                "Check your network connection and retry."
            ) from url_err

    def query_crux_record(
        self,
        url_or_origin: str,
        form_factor: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queries Chrome UX Report API for real-user field metrics."""
        key_val, _ = resolve_api_key(api_key or self.api_key)
        target, is_origin = normalize_target(url_or_origin)

        payload: Dict[str, Any] = {}
        if is_origin:
            payload["origin"] = target
        else:
            payload["url"] = target

        if form_factor and form_factor.strip():
            ff_upper = form_factor.strip().upper()
            if ff_upper not in VALID_FORM_FACTORS:
                raise ValueError(
                    f"[INPUT_FIXABLE] Invalid form_factor '{form_factor}'. "
                    f"Must be one of: {', '.join(sorted(VALID_FORM_FACTORS))}"
                )
            if ff_upper != "ALL_FORM_FACTORS":
                payload["formFactor"] = ff_upper

        req_url = CRUX_QUERY_ENDPOINT
        if key_val:
            req_url = f"{req_url}?key={urllib.parse.quote_plus(key_val)}"

        raw_resp = self._execute_http(req_url, method="POST", data=payload)
        record = raw_resp.get("record", {})
        return extract_crux_metrics(record)

    def query_crux_history(
        self,
        url_or_origin: str,
        form_factor: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queries Chrome UX Report History API for 28-day historical metrics."""
        key_val, _ = resolve_api_key(api_key or self.api_key)
        target, is_origin = normalize_target(url_or_origin)

        payload: Dict[str, Any] = {}
        if is_origin:
            payload["origin"] = target
        else:
            payload["url"] = target

        if form_factor and form_factor.strip():
            ff_upper = form_factor.strip().upper()
            if ff_upper in VALID_FORM_FACTORS and ff_upper != "ALL_FORM_FACTORS":
                payload["formFactor"] = ff_upper

        req_url = CRUX_HISTORY_ENDPOINT
        if key_val:
            req_url = f"{req_url}?key={urllib.parse.quote_plus(key_val)}"

        raw_resp = self._execute_http(req_url, method="POST", data=payload)
        record = raw_resp.get("record", {})
        collection_periods = record.get("collectionPeriods", [])
        metrics_data = record.get("metrics", {})

        history_summary: Dict[str, Any] = {
            "target": target,
            "is_origin": is_origin,
            "collection_periods_count": len(collection_periods),
            "collection_periods": collection_periods,
            "metrics": {},
        }

        metric_mapping = {
            "largest_contentful_paint": "lcp",
            "interaction_to_next_paint": "inp",
            "cumulative_layout_shift": "cls",
            "first_contentful_paint": "fcp",
            "experimental_time_to_first_byte": "ttfb",
        }

        for raw_name, clean_name in metric_mapping.items():
            if raw_name in metrics_data:
                item = metrics_data[raw_name]
                p75_series = item.get("percentilesTimeseries", {}).get("p75s", [])
                unit = METRIC_THRESHOLDS.get(raw_name, {}).get("unit", "ms")
                history_summary["metrics"][clean_name] = {
                    "p75_timeseries": p75_series,
                    "unit": unit,
                    "latest_p75": p75_series[-1] if p75_series else None,
                }

        return history_summary

    def run_pagespeed_audit(
        self,
        url: str,
        strategy: str = "mobile",
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs Google PageSpeed Insights lab audit and returns Lighthouse score and diagnostics."""
        key_val, _ = resolve_api_key(api_key or self.api_key)
        target, _ = normalize_target(url)

        strat = strategy.strip().lower()
        if strat not in ("mobile", "desktop"):
            raise ValueError("[INPUT_FIXABLE] Strategy must be either 'mobile' or 'desktop'.")

        params = {
            "url": target,
            "strategy": strat,
            "category": "performance",
        }
        if key_val:
            params["key"] = key_val

        query_str = urllib.parse.urlencode(params)
        req_url = f"{PAGESPEED_ENDPOINT}?{query_str}"

        raw_resp = self._execute_http(req_url, method="GET")

        lh = raw_resp.get("lighthouseResult", {})
        categories = lh.get("categories", {})
        perf = categories.get("performance", {})
        perf_score = int(round((perf.get("score") or 0.0) * 100))

        audits = lh.get("audits", {})

        def get_audit_item(name: str) -> Dict[str, Any]:
            a = audits.get(name, {})
            return {
                "score": a.get("score"),
                "displayValue": a.get("displayValue"),
                "numericValue": a.get("numericValue"),
            }

        lab_metrics = {
            "first_contentful_paint": get_audit_item("first-contentful-paint"),
            "speed_index": get_audit_item("speed-index"),
            "largest_contentful_paint": get_audit_item("largest-contentful-paint"),
            "total_blocking_time": get_audit_item("total-blocking-time"),
            "cumulative_layout_shift": get_audit_item("cumulative-layout-shift"),
            "interactive": get_audit_item("interactive"),
        }

        # Extract top optimization opportunities
        opportunities = []
        for audit_id, audit in audits.items():
            details = audit.get("details", {})
            if details.get("type") == "opportunity" and (audit.get("score") or 0.0) < 0.9:
                overall_savings_ms = details.get("overallSavingsMs")
                overall_savings_bytes = details.get("overallSavingsBytes")
                opportunities.append({
                    "id": audit_id,
                    "title": audit.get("title"),
                    "displayValue": audit.get("displayValue"),
                    "description": audit.get("description"),
                    "score": audit.get("score"),
                    "savings_ms": overall_savings_ms,
                    "savings_bytes": overall_savings_bytes,
                })

        # Sort opportunities by estimated ms savings descending
        opportunities.sort(key=lambda x: (x.get("savings_ms") or 0), reverse=True)

        return {
            "url": target,
            "strategy": strat,
            "performance_score": perf_score,
            "lab_metrics": lab_metrics,
            "opportunities_count": len(opportunities),
            "top_opportunities": opportunities[:5],
        }
