# Core Web Vitals MCP Server (`core-web-vitals-mcp`)

FastMCP server exposing Google Chrome User Experience Report (CrUX) and PageSpeed Insights APIs for real-user Core Web Vitals (LCP, INP, CLS), 28-day field history trends, and Lighthouse lab performance audits.

The definitive Core Web Vitals diagnostics engine for AI coding agents (Claude, Cursor, Copilot, Antigravity).

---

## 1. Quickstart

Run directly without installing via `uvx` (Python) or `npx` (Node):

### Via Python (`uvx`)
```bash
uvx core-web-vitals-mcp
```

### Via Node (`npx`)
```bash
npx -y core-web-vitals-tools-mcp
```

---

## 2. MCP Client Configuration

Add to your MCP client config (`claude_desktop_config.json`, `cursor.json`, or Antigravity):

```json
{
  "mcpServers": {
    "core-web-vitals": {
      "command": "uvx",
      "args": ["core-web-vitals-mcp"],
      "env": {
        "GOOGLE_API_KEY": "your_google_api_key_here"
      }
    }
  }
}
```

Or using `npx`:
```json
{
  "mcpServers": {
    "core-web-vitals": {
      "command": "npx",
      "args": ["-y", "core-web-vitals-tools-mcp"],
      "env": {
        "GOOGLE_API_KEY": "your_google_api_key_here"
      }
    }
  }
}
```

---

## 3. Google API Authentication & Keyless Mode

- **Works Keyless Out-of-the-Box**: PageSpeed Insights lab audits (`audit_pagespeed`) run with **zero API keys and zero configuration**.
- **Chrome UX Report (CrUX)**: 28-day field data requires a free Google Cloud API key (up to 150 requests/minute). When running keyless, the server gracefully returns synthetic lab metrics and instructs your AI agent how to enable field data.
- **Built-in Client Throttling**: Automatically throttles requests (1.5s for keyless PageSpeed, 0.5s for keyed PageSpeed, 0.4s for CrUX) and caches repeated queries to strictly honor Google's free usage limits and prevent HTTP 429 errors.

To configure an API key:
1. Follow the official Google guide: [PageSpeed Insights API - Get Started (API Key)](https://developers.google.com/speed/docs/insights/v5/get-started#APIKey).
2. Or call `skill_read(name="google-api-setup")` directly from your AI agent for step-by-step instructions.
3. Set your environment variable:
   ```bash
   export GOOGLE_API_KEY="AIzaSy..."
   # or
   export CRUX_API_KEY="AIzaSy..."
   ```

---

## 4. Tools

| Tool | Parameters | Description |
|---|---|---|
| `get_crux_metrics` | `url`, `form_factor="ALL_FORM_FACTORS"`, `api_key` | Query Google CrUX API for real-user field metrics: LCP, INP, CLS, FCP, TTFB, and overall Core Web Vitals assessment. Falls back to PageSpeed when keyless. |
| `get_crux_history` | `url_or_origin`, `form_factor`, `api_key` | Query Google CrUX History API for 28-day historical field metric trends across 25+ weekly collection periods. |
| `audit_pagespeed` | `url`, `strategy="mobile"`, `api_key` | Run Google PageSpeed Insights lab audit for Lighthouse performance score (0-100), Speed Index, TBT, LCP, and top savings opportunities (works keyless!). |
| `doctor` | `api_key` | Diagnostic utility verifying Google API key configuration, testing endpoint connectivity, and verifying test bed readiness. |
| `skills_list` | *(none)* | Lists dynamic Core Web Vitals diagnostic, remediation, and setup playbooks. |
| `skill_read` | `name` | Fetches operational engineering playbooks: `google-api-setup`, `lcp-optimization`, `inp-debugging`, or `cls-remediation`. |
| `check_for_updates` | `force=False` | Queries PyPI for newer versions and upgrade commands. |

---

## 5. Playbook Skills

The server dynamically dissociates actionable engineering playbooks from the core runtime:
* **`google-api-setup`**: Official setup guide to obtain a free Google Cloud API key, enable CrUX/PageSpeed APIs, and manage free usage limits per [developers.google.com](https://developers.google.com/speed/docs/insights/v5/get-started#APIKey).
* **`lcp-optimization`**: 4-phase breakdown (TTFB, Load Delay, Load Duration, Render Delay), image format conversion, preloading, and render blocking mitigation.
* **`inp-debugging`**: Interactive latency breakdown (Input Delay, Processing, Presentation Delay), task chunking with `scheduler.yield()`, and long task mitigation.
* **`cls-remediation`**: Aspect-ratio reservation, fallback font metric overrides (`size-adjust`), and layout stability patterns.

---

## 6. Telemetry & Privacy

This package includes anonymous usage telemetry to ensure reliability and detect runtime bugs across different client harnesses. Telemetry adheres strictly to Schema v2:
* **Opt-Out**: Strictly respects `DO_NOT_TRACK=1`, `DISABLE_TELEMETRY=1`, `MCP_TELEMETRY_OPT_OUT=1`, or `CORE_WEB_VITALS_TELEMETRY=false`.
* **Zero PII**: No user URLs, personal identifiers, or authentication keys are ever captured.
