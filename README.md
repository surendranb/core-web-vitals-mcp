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

## 3. Google API Authentication

While PageSpeed Insights can execute lab audits under limited public quota, Chrome UX Report (CrUX) queries require an authorized Google API Key:

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project or create a new one.
3. Navigate to **APIs & Services** -> **Library** and enable:
   - **Chrome UX Report API**
   - **PageSpeed Insights API**
4. Navigate to **APIs & Services** -> **Credentials** -> **Create Credentials** -> **API key**.
5. Set the environment variable:
   ```bash
   export GOOGLE_API_KEY="AIzaSy..."
   # or
   export CRUX_API_KEY="AIzaSy..."
   ```

---

## 4. Tools

| Tool | Parameters | Description |
|---|---|---|
| `get_crux_metrics` | `url`, `form_factor="ALL_FORM_FACTORS"`, `api_key` | Query Google CrUX API for real-user field metrics: LCP, INP, CLS, FCP, TTFB, and overall Core Web Vitals assessment (PASSED / FAILED). |
| `get_crux_history` | `url_or_origin`, `api_key` | Query Google CrUX History API for 28-day historical field metric trends across 25+ weekly collection periods. |
| `audit_pagespeed` | `url`, `strategy="mobile"`, `api_key` | Run Google PageSpeed Insights lab audit for Lighthouse performance score (0-100), Speed Index, TBT, LCP, and top savings opportunities. |
| `doctor` | `api_key` | Diagnostic utility verifying Google API key configuration, testing endpoint connectivity, and verifying test bed readiness. |
| `skills_list` | *(none)* | Lists dynamic Core Web Vitals diagnostic and remediation playbooks. |
| `skill_read` | `name` | Fetches operational engineering playbooks: `lcp-optimization`, `inp-debugging`, or `cls-remediation`. |
| `check_for_updates` | `force=False` | Queries PyPI for newer versions and upgrade commands. |

---

## 5. Playbook Skills

The server dynamically dissociates actionable engineering playbooks from the core runtime:
* **`lcp-optimization`**: 4-phase breakdown (TTFB, Load Delay, Load Duration, Render Delay), image format conversion, preloading, and render blocking mitigation.
* **`inp-debugging`**: Interactive latency breakdown (Input Delay, Processing, Presentation Delay), task chunking with `scheduler.yield()`, and long task mitigation.
* **`cls-remediation`**: Aspect-ratio reservation, fallback font metric overrides (`size-adjust`), and layout stability patterns.

---

## 6. Telemetry & Privacy

This package includes anonymous usage telemetry to ensure reliability and detect runtime bugs across different client harnesses. Telemetry adheres strictly to Schema v2:
* **Opt-Out**: Strictly respects `DO_NOT_TRACK=1`, `DISABLE_TELEMETRY=1`, `MCP_TELEMETRY_OPT_OUT=1`, or `CORE_WEB_VITALS_TELEMETRY=false`.
* **Zero PII**: No user URLs, personal identifiers, or authentication keys are ever captured.
