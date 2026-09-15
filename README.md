# 🤖 Web Automation Agent

A Python terminal agent that opens a **real Chromium browser**, navigates to a webpage, and uses a configurable **AI vision model** (default: Qwen3-VL-30B-A3B-Instruct on HuggingFace) to propose browser actions from screenshots.

> Think of it as a robot that can see your screen and use a mouse and keyboard, guided by a powerful AI.

---

## ✨ How It Works

Every step of the loop:

```
📸 Take Screenshot  →  🤖 Ask AI "What next?"  →  🖱️ Execute Action  →  🔁 Repeat
```

1. A screenshot of the browser is taken and compressed
2. The screenshot + task description are sent to the configured vision model via HuggingFace's API
3. The AI responds with a tool call — e.g., `click_on_screen(x=640, y=385)` or `send_keys("hello@email.com")`
4. That action is executed in the real browser via Playwright
5. Repeat until the AI signals `DONE`

---

## 🚀 Quick Start

### 1. Clone and Set Up

```bash
git clone <your-repo-url>
cd "Web Automation Agent"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Your API Key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your HuggingFace API token:

```
HF_API_TOKEN=hf_your_token_here
```

> Get your token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 3. Set Your Task

Edit `src/main.py` to define the instructions. The URL can be part of the
instructions; a separate `START_URL` is not required:

```python
TASK = "Open https://example.com/contact and fill out the contact form with name 'Alex' and email 'alex@email.com'"
```

### 4. Run It

```bash
source .venv/bin/activate
python -m src.main
```

A Chromium browser window will appear and the agent will start working. Watch it go!

When no start URL is supplied, the agent opens an isolated blank page and
uses its controlled `navigate_to_url` action. The first navigation establishes
the task-scoped origin; later navigation and network requests outside that
origin are blocked. For higher-assurance tasks, pass an explicit
`allowed_origins` set to `run_agent` instead of using bootstrap discovery.

---

## 📁 Project Structure

```
Web Automation Agent/
├── src/
│   ├── main.py              # Entry point — define task instructions here
│   ├── agent/
│   │   ├── agent.py         # Capture/provider/action/verification loop
│   │   ├── actions.py       # Typed actions and coordinate scaling
│   │   ├── controller.py    # Single browser side-effect boundary
│   │   ├── policy.py        # Origin and approval policy
│   │   ├── prompt.py        # Screenshot-driven instructions
│   │   ├── recorded.py      # Offline provider adapter
│   │   ├── trace.py         # Sanitized JSONL traces
│   │   └── verification.py  # Independent completion predicates
│   ├── tools/
│   │   ├── state.py         # Isolated browser state
│   │   ├── browser.py       # Context, navigation, network boundary
│   │   ├── screenshot.py    # Capture and metadata
│   │   ├── mouse.py         # Click and double-click
│   │   ├── keyboard.py      # Type text and press keys
│   │   └── scroll.py        # Scroll up/down
│   └── utils/
│       ├── config.py        # Load HF_API_TOKEN from .env
│       └── logger.py        # Colored timestamped logs
├── fixtures/                # Owned local fixture server and task manifest
├── tests/                   # Deterministic offline tests
├── tools/                   # Trace viewer
├── evaluate.py              # Recorded-run evaluation entry point
├── requirements-dev.txt     # Runtime dependencies plus pytest
├── requirements.txt         # Pinned runtime dependencies
└── README.md                # This file
```

---

## ⚙️ Configuration

All configuration is via the `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_API_TOKEN` | ✅ for live runs | Your HuggingFace API token for model inference |
| `WEB_AGENT_MODEL` | No | Model name; defaults to `Qwen/Qwen3-VL-30B-A3B-Instruct` |

The token is used to authenticate requests to HuggingFace's OpenAI-compatible inference API.

---

## 🛠️ Available Actions

The model can request these actions. Every side effect passes through the controller:

| Tool | What It Does |
|------|-------------|
| `open_browser()` | Launch isolated Chromium browser |
| `navigate_to_url(url)` | Go to a URL |
| `take_screenshot()` | Capture current browser state |
| `click_on_screen(x, y)` | Click at pixel coordinates |
| `double_click(x, y)` | Double-click at pixel coordinates |
| `send_keys(text)` | Type text at cursor position |
| `press_key(key)` | Press a keyboard key |
| `scroll(direction, amount)` | Scroll page up or down |
| `wait(seconds)` | Wait for a bounded period |
| `done()` | Request trusted completion verification |

---

## 📦 Requirements

- **Python 3.10+**
- **HuggingFace account** with API token (free tier works)

### Python Packages

```
playwright          # Browser control
openai              # SDK for HuggingFace's OpenAI-compatible API
Pillow              # Screenshot compression
python-dotenv       # .env file loading
```

Install all with:

```bash
pip install -r requirements.txt
playwright install chromium
```

For deterministic tests, also install `requirements-dev.txt`.

## Reliability and safety architecture

The loop is intentionally split into capture → provider → typed action → policy/controller → browser → observation → trusted verification. The model only proposes actions. `src/agent/actions.py` validates tool names, coordinates, text, keys, waits, navigation and budgets. `src/agent/controller.py` is the single side-effect boundary, including keyboard shortcuts and navigation.

`ActionPolicy` compares parsed scheme/host/port origins exactly, binds approvals to an action, origin, target and expiry, and fails closed when no origin is configured. Protected Enter-key submissions are enabled only by trusted task configuration (`protect_enter=True`); normal search actions are not treated as form submissions. Browser episodes use a fresh Playwright context with no inherited storage, blocked service workers, disabled downloads and request interception. This is a task-scoped local boundary, not a guarantee against every browser or operating-system side channel; arbitrary sensitive-action classification from screenshots remains a limitation. Malformed model output is recorded as `invalid_model_output`, not as a policy denial.

The model's `done` is never success by itself. Configure `completion_predicate` with a trusted fixture/server/application assertion to obtain `verified_success`; otherwise the result is `unverified_done`. Endings are recorded as `verified_success`, `unverified_done`, `verification_failed`, `policy_blocked`, `budget_exhausted`, `provider_error`, `browser_error`, or `invalid_model_output`.

## Offline evaluation and traces

`RecordedResponseAdapter` runs the loop without an inference provider. The local fixture server and task manifest are in `fixtures/`; the manifest contains development and held-out scenario specifications. JSONL traces are sanitized and kept outside page content:

```bash
python fixtures/site.py
python evaluate.py --responses path/to/responses.jsonl
python tools/trace_viewer.py traces/episode.jsonl > trace.html
```

The viewer escapes page/model text. Traces can contain screenshots and should be retained only as long as needed, then deleted. Replay is inspection-only; recorded side effects are not automatically re-executed.

Run deterministic checks with:

```bash
python -m pytest -q
```

The shipped tests cover action validation and scaling, exact origin comparison, approval expiry and replay, independent DONE verification, recorded responses, and secret redaction. They verify controller behavior, not live-model competence. Live YouTube evaluation remains pending and should use a disposable profile and a non-sensitive task.

The current fixture server implements the representative `/` form and
`/result` flow. `fixtures/tasks.json` is the versioned scenario contract for
the planned development and held-out matrix; the remaining routes are not
claimed as implemented until they have corresponding server behavior and
integration tests.

## Checklist

```bash
python -m pytest -q                         # deterministic checks
python -m compileall -q src fixtures tools  # syntax/import compilation
python evaluate.py --responses fixtures/recorded_responses.jsonl
python fixtures/site.py                     # optional local fixture server
```

Expected baseline: all deterministic tests pass, recorded evaluation reports
`run_type: recorded`, and the fixture responds to `GET /` with a form and
`POST /submit` with a redirect to `/result`. A live model run requires
`HF_API_TOKEN`, incurs provider inference usage, and is intentionally not part
of offline CI.

---

## 🏗️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Browser control | [Playwright](https://playwright.dev/python/) | Automate real Chromium |
| AI model | `WEB_AGENT_MODEL` (default `Qwen/Qwen3-VL-30B-A3B-Instruct`) | Vision + reasoning |
| AI API | [HuggingFace Inference API](https://huggingface.co/docs/api-inference/) | OpenAI-compatible hosting |
| API SDK | [openai](https://github.com/openai/openai-python) | Talk to HuggingFace API |
| Screenshot handling | [Pillow](https://pillow.readthedocs.io/) | Encode screenshots for the provider |
| Config | [python-dotenv](https://github.com/theskumar/python-dotenv) | Load API keys from .env |

---



## 💡 Key Design Highlights

### Custom agent loop
The project uses the OpenAI-compatible Python client directly. The custom async loop injects a fresh screenshot on every iteration and keeps capture, provider calls, parsing, policy, action execution, and verification separate.

### Screenshot handling
The agent stores a full-resolution PNG for local inspection and sends a JPEG representation to the provider. Image byte size is reported separately from token usage; the project makes no token-savings claim unless the provider returns usage data.

### HuggingFace as OpenAI API
HuggingFace exposes an OpenAI-compatible endpoint at `https://router.huggingface.co/v1`. The standard `openai` Python SDK is pointed at that endpoint, with the model selected through `WEB_AGENT_MODEL`.

### Self-Correcting Agent
Tools return error strings instead of raising exceptions. The AI sees errors in the next step and adjusts its approach automatically.

---
