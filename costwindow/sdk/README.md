# CostWindow

The control layer for autonomous AI spend. Track every call, set hard budgets,
and kill any process instantly — for [CostWindow](https://costwindow.com).

## The fastest way: the drop-in proxy (no SDK, any language)

Change one line — your AI client's base URL — and every call is tracked, with a
hard kill switch in front of it. Killed or over-budget processes are refused
*before* the provider is called. Your provider API key passes straight through
and is never stored.

```python
# Anthropic (Python)
client = anthropic.Anthropic(
    base_url="https://api.costwindow.com/proxy/anthropic/cw_live_your_key",
)

# OpenAI (Python) — note the /v1
client = openai.OpenAI(
    base_url="https://api.costwindow.com/proxy/openai/cw_live_your_key/v1",
)
```

```javascript
// Anthropic (JS/TS) — works for any language, just set the base URL
const client = new Anthropic({
  baseURL: "https://api.costwindow.com/proxy/anthropic/cw_live_your_key",
});

// OpenAI (JS/TS) — note the /v1
const client = new OpenAI({
  baseURL: "https://api.costwindow.com/proxy/openai/cw_live_your_key/v1",
});
```

```bash
# Or straight cURL — same idea in any stack
curl https://api.costwindow.com/proxy/anthropic/cw_live_your_key/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" -d '{ "model": "claude-sonnet-4-6", ... }'
```

Optionally add a header `X-CostWindow-Label: my-process` to name the process
(otherwise it's `proxy-anthropic` / `proxy-openai` / `proxy-google`).

Get your `cw_live_` key from **Settings** in your dashboard.

---

## The Python SDK (when you can't change the base URL)

For scripts where the proxy isn't practical, this SDK reports usage after each
call.

```bash
pip install costwindow
```

```python
from costwindow import CostWindow
import anthropic

cw = CostWindow(api_key="cw_live_...")           # backend defaults to api.costwindow.com
client = cw.wrap_anthropic(anthropic.Anthropic())

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Hello"}],
    cw_label="my-script",
)
```

`cw.wrap_openai()` and `cw.wrap_gemini()` work the same way.

### Kill switch for cron jobs

```python
from costwindow import CostWindow, CostWindowProcessDisabledError

cw = CostWindow(api_key="cw_live_...")
if not cw.is_active("my-cron"):
    raise SystemExit("Process killed in CostWindow — skipping run.")
```

CostWindow never breaks your script: if the service is unreachable, errors are
logged to `~/.costwindow/logs/` and swallowed. The only exception that
propagates is `CostWindowProcessDisabledError` — raised when a wrapped call hits
a process you've kill-switched in the dashboard.

---

MIT licensed. Questions → costwindow.com.
