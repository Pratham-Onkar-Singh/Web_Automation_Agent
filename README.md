# 🤖 Web Automation Agent

A Python terminal agent that opens a **real Chromium browser**, navigates to a webpage, and uses an **AI vision model** (Qwen2.5-VL-72B on HuggingFace) to autonomously fill out forms and complete web tasks — by looking at screenshots and deciding what to click or type.

> Think of it as a robot that can see your screen and use a mouse and keyboard, guided by a powerful AI.

---

## ✨ How It Works

Every step of the loop:

```
📸 Take Screenshot  →  🤖 Ask AI "What next?"  →  🖱️ Execute Action  →  🔁 Repeat
```

1. A screenshot of the browser is taken and compressed
2. The screenshot + task description are sent to **Qwen2.5-VL-72B** (a vision+language model) via HuggingFace's API
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

Edit `src/main.py` to define what you want the agent to do:

```python
TASK = "Fill out the contact form with name 'Alex' and email 'alex@email.com'"
START_URL = "https://example.com/contact"
```

### 4. Run It

```bash
python src/main.py
```

A Chromium browser window will appear and the agent will start working. Watch it go!

---

## 📁 Project Structure

```
Web Automation Agent/
├── src/
│   ├── main.py              # Entry point — define your task here
│   ├── agent/
│   │   ├── agent.py         # Core agent loop + HuggingFace client
│   │   └── prompt.py        # System prompt + tool JSON schemas
│   ├── tools/
│   │   ├── state.py         # Shared browser state singleton
│   │   ├── browser.py       # Open/close browser
│   │   ├── screenshot.py    # Capture + compress screenshots
│   │   ├── mouse.py         # Click and double-click
│   │   ├── keyboard.py      # Type text
│   │   └── scroll.py        # Scroll up/down
│   └── utils/
│       ├── config.py        # Load HF_API_TOKEN from .env
│       └── logger.py        # Colored timestamped logs
├── docs/
│   ├── ARCHITECTURE.md      # Deep-dive architecture + design decisions
│   ├── HOW_IT_WORKS.md      # Beginner-friendly explanation
│   └── TOOLS_REFERENCE.md   # Complete reference for all 7 tools
├── .env                     # Your secrets (never commit this!)
├── .env.example             # Template for .env
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## ⚙️ Configuration

All configuration is via the `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_API_TOKEN` | ✅ Yes | Your HuggingFace API token for model inference |

The token is used to authenticate requests to HuggingFace's OpenAI-compatible inference API.

---

## 🛠️ Available Tools

The AI can call 7 tools to control the browser:

| Tool | What It Does |
|------|-------------|
| `open_browser()` | Launch Chromium browser |
| `navigate_to_url(url)` | Go to a URL |
| `take_screenshot()` | Capture current browser state |
| `click_on_screen(x, y)` | Click at pixel coordinates |
| `double_click(x, y)` | Double-click at pixel coordinates |
| `send_keys(text)` | Type text at cursor position |
| `scroll(direction, amount)` | Scroll page up or down |

→ Full reference: [docs/TOOLS_REFERENCE.md](docs/TOOLS_REFERENCE.md)

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

---

## 🏗️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Browser control | [Playwright](https://playwright.dev/python/) | Automate real Chromium |
| AI model | [Qwen2.5-VL-72B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct) | Vision + reasoning |
| AI API | [HuggingFace Inference API](https://huggingface.co/docs/api-inference/) | OpenAI-compatible hosting |
| API SDK | [openai](https://github.com/openai/openai-python) | Talk to HuggingFace API |
| Screenshot compression | [Pillow](https://pillow.readthedocs.io/) | Reduce image size ~94% |
| Config | [python-dotenv](https://github.com/theskumar/python-dotenv) | Load API keys from .env |

---



## 💡 Key Design Highlights

### Custom Agent Loop (Not SDK Runner)
The OpenAI Agents SDK only passes text between steps. Our agent needs fresh screenshots injected at every iteration, so we write our own `async` loop with full control over the message payload.

### Screenshot Compression
Full 1280×720 PNG ≈ 500KB ≈ 750K tokens. Compressed 640×360 JPEG at quality 60 ≈ 30KB ≈ 45K tokens. **~94% token savings per step.**

### HuggingFace as OpenAI API
HuggingFace exposes an OpenAI-compatible endpoint at `https://router.huggingface.co/v1`. We use the standard `openai` Python SDK, just pointing it at a different URL. The `:cheapest` model suffix auto-routes to the lowest-cost available provider.

### Self-Correcting Agent
Tools return error strings instead of raising exceptions. The AI sees errors in the next step and adjusts its approach automatically.

---


