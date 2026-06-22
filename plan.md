# 🤖 Website Automation Agent — Plan

> Terminal-only AI agent. Python + Playwright + OpenAI Agents SDK + HuggingFace.
> Run `python src/main.py`, watch the browser fill a form by itself.

---

## Tech Stack

| What | Tool |
|------|------|
| Language | **Python 3.10+** |
| Browser control | **Playwright for Python** |
| Agent framework | **OpenAI Agents SDK** (`openai-agents`) |
| AI provider | **HuggingFace Inference API** (OpenAI-compatible) |
| Vision model | **Qwen/Qwen2.5-VL-72B-Instruct:cheapest** (~$0.05/1M tokens) |
| Config | **python-dotenv** |

### Why These Choices

- **Playwright** — Pyppeteer is dead (unmaintained since 2022). Playwright is the modern Python browser automation lib. Assignment recommends it too.
- **OpenAI Agents SDK** — handles the agent loop, tool calling, and orchestration for us. We define tools with `@function_tool`, SDK does the rest.
- **HuggingFace** — OpenAI-compatible API at `https://router.huggingface.co/v1`. Same interface, 50x cheaper.
- **Qwen2.5-VL-72B** — vision model that sees screenshots + supports tool calling. Cheapest option that actually works.

---

## How It Works

```
You run: python src/main.py
    │
    ▼
Agent starts
    │
    ├── Opens Chromium browser (visible window, 1280×720)
    ├── Navigates to the target URL
    │
    │   ┌─── AGENT LOOP (we write this) ─────────────┐
    │   │                                              │
    │   │  1. take_screenshot                          │
    │   │  2. Send screenshot AS IMAGE to Qwen2.5-VL   │
    │   │  3. AI sees the page, returns a tool call    │
    │   │  4. We execute the tool (click/type/scroll)  │
    │   │  5. Back to step 1                           │
    │   │                                              │
    │   └─── Stops when AI says "done" ────────────────┘
    │
    ├── Closes browser
    ▼
Done. Screenshots saved in screenshots/ folder.
```

### ⚠️ Why We Write Our Own Loop (Important)

The OpenAI Agents SDK's `@function_tool` returns **text only**. But for vision to work, the AI model needs to receive the screenshot **as an image** (not a text string). The SDK's `Runner.run()` doesn't automatically inject images between tool calls.

**So we write a simple manual loop:**
1. Take screenshot → compress to JPEG → encode base64
2. Build a message with the image: `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}`
3. Call the model with `client.chat.completions.create()` (using the OpenAI SDK directly)
4. Parse the tool call from the response
5. Execute the tool
6. Repeat

We still use the **OpenAI Agents SDK's `Agent` class** for defining the agent and its tools. We just handle the loop ourselves so we can inject images properly.

### Screenshot Compression (Saves ~75% tokens)

Full 1280×720 PNG screenshots are huge. Before sending to AI:
- Resize to **640×360** (half resolution — still readable)
- Convert to **JPEG quality 60** (much smaller than PNG)
- This cuts token cost by ~75% per screenshot

```python
from PIL import Image
import io, base64

def compress_screenshot(png_bytes):
    img = Image.open(io.BytesIO(png_bytes))
    img = img.resize((640, 360))  # Half size
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=60)
    return base64.b64encode(buffer.getvalue()).decode()
```

---

## Project Structure

```
Web Automation Agent/
├── src/
│   ├── main.py               # Entry point — define task, run agent loop
│   ├── agent/
│   │   ├── agent.py           # Agent loop + HF model provider
│   │   └── prompt.py          # System prompt + tool schemas for AI
│   ├── tools/
│   │   ├── state.py           # Shared browser state (page, browser refs)
│   │   ├── browser.py         # open_browser, navigate_to_url, close_browser
│   │   ├── screenshot.py      # take_screenshot + compress for AI
│   │   ├── mouse.py           # click_on_screen, double_click
│   │   ├── keyboard.py        # send_keys
│   │   └── scroll.py          # scroll up/down
│   └── utils/
│       ├── logger.py          # Colored console logs with timestamps
│       └── config.py          # Load .env, export settings
├── screenshots/               # Auto-saved screenshots (gitignored)
├── .env                       # HF_API_TOKEN=hf_xxxxx
├── .gitignore                 # __pycache__, .env, screenshots/
├── requirements.txt           # All pip dependencies
├── README.md
└── plan.md                    # This file
```

### Shared Browser State (`state.py`)

All tools need access to the same browser page. One shared module:

```python
# src/tools/state.py
class BrowserState:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.step_count = 0

state = BrowserState()  # Single global instance, imported by all tools
```

---

## How HuggingFace Plugs Into OpenAI Agents SDK

The SDK expects an OpenAI-compatible API. HuggingFace provides exactly that. We create a custom `ModelProvider`:

```python
from openai import AsyncOpenAI
from agents import ModelProvider, OpenAIChatCompletionsModel, set_tracing_disabled
import os

# Disable OpenAI tracing (we're not using OpenAI servers)
set_tracing_disabled(True)

# Point the OpenAI client at HuggingFace
client = AsyncOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_API_TOKEN")
)

class HuggingFaceProvider(ModelProvider):
    def get_model(self, model_name=None):
        return OpenAIChatCompletionsModel(
            model=model_name or "Qwen/Qwen2.5-VL-7B-Instruct:cheapest",
            openai_client=client
        )
```

The `:cheapest` suffix tells HuggingFace to auto-route to the cheapest available provider for that model.

We also use `client` directly in our agent loop to send image messages — the SDK's Agent class is used for tool definitions, but the loop calls `client.chat.completions.create()` with image content.

---

## The 7 Tools

Each tool is a Python function decorated with `@function_tool`. The SDK auto-discovers the function signature and docstring.

```python
from agents import function_tool

@function_tool
async def click_on_screen(x: int, y: int) -> str:
    """Click at pixel coordinates (x, y) on the browser page."""
    await page.mouse.click(x, y)
    return f"Clicked at ({x}, {y})"
```

| Tool | What It Does | Playwright API |
|------|-------------|----------------|
| `open_browser()` | Launch Chromium (1280×720, visible) | `chromium.launch()`, `new_page()` |
| `navigate_to_url(url)` | Go to URL, wait for load | `page.goto(url)` |
| `take_screenshot()` | Save PNG + return base64 for AI | `page.screenshot()` |
| `click_on_screen(x, y)` | Click at pixel coordinates | `page.mouse.click(x, y)` |
| `send_keys(text)` | Type text into focused field | `page.keyboard.type(text)` |
| `scroll(direction, amount)` | Scroll page up or down | `page.mouse.wheel()` |
| `double_click(x, y)` | Double-click at coordinates | `page.mouse.dblclick(x, y)` |

Every tool returns a string result. On error, returns the error message — AI sees it and adapts.

---

## The Agent Definition

```python
from agents import Agent, Runner, RunConfig

agent = Agent(
    name="BrowserAgent",
    instructions="""You are a browser automation agent. You control a real browser.
    
    The viewport is 1280×720 pixels. When you see a screenshot, identify 
    UI elements by their pixel coordinates and interact with them using 
    the available tools.
    
    Your task will be given to you. Execute it step by step.
    When the task is complete, respond with DONE.""",
    tools=[
        open_browser,
        navigate_to_url,
        take_screenshot,
        click_on_screen,
        send_keys,
        scroll,
        double_click,
    ]
)
```

---

## The Agent Loop (Core Logic)

This is what `agent.py` actually does:

```python
async def run_agent(task: str):
    # 1. Setup
    await open_browser()
    await navigate_to_url("https://ui.shadcn.com/docs/forms/react-hook-form")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task}
    ]
    
    for step in range(25):  # Max 25 iterations safety cap
        # 2. OBSERVE — take screenshot, compress, encode
        screenshot_b64 = await take_screenshot()  # Returns compressed base64
        
        # 3. THINK — send image to AI
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Here is the current screenshot. What should I do next?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}}
            ]
        })
        
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-7B-Instruct:cheapest",
            messages=messages,
            tools=TOOL_SCHEMAS,      # Tool definitions from prompt.py
            tool_choice="auto"
        )
        
        # 4. ACT — parse and execute tool call
        msg = response.choices[0].message
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            result = await execute_tool(tool_call.function.name, tool_call.function.arguments)
            
            # Add tool result to conversation
            messages.append(msg)  # Assistant's tool call
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
            
            log_action(tool_call.function.name, result)
        else:
            # No tool call — AI is done or responding with text
            if "done" in msg.content.lower():
                break
    
    await close_browser()
```

## The Entry Point

```python
# src/main.py
import asyncio
from agent.agent import run_agent

TASK = """
1. Find the form on the page (it has Name and Description fields)
2. You may need to scroll down to find it
3. Click on the Name field and type "Lingam Raghavendra"
4. Click on the Description field and type "Automated by Web Automation Agent"
5. Click the Submit button
6. Take a final screenshot to confirm, then say DONE
"""

asyncio.run(run_agent(TASK))
```

Run: `python src/main.py`

---

## Build Order

### Phase 1: Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux

# Install dependencies
pip install playwright openai-agents python-dotenv
playwright install chromium     # Downloads browser binary (~150MB)
```

Create `.env`:
```
HF_API_TOKEN=hf_your_token_here
```

> Get token free from https://huggingface.co/settings/tokens

Create `requirements.txt`:
```
playwright>=1.52.0
openai-agents>=0.1.0
python-dotenv>=1.1.0
```

### Phase 2: Build Tools

Build and test each tool individually before connecting the agent:

1. `browser.py` → verify Chromium opens and closes
2. `screenshot.py` → verify PNG saves to `screenshots/`
3. `mouse.py` → verify click and double-click work
4. `keyboard.py` → verify typing works
5. `scroll.py` → verify scroll works

Quick test:
```python
# test_tools.py (delete later)
import asyncio
from playwright.async_api import async_playwright

async def test():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page(viewport={"width": 1280, "height": 720})
    await page.goto("https://example.com")
    await page.screenshot(path="screenshots/test.png")
    print("Screenshot saved!")
    await browser.close()
    await pw.stop()

asyncio.run(test())
```

### Phase 3: Build Agent

1. `config.py` — load HF token from `.env`
2. `agent.py` — `HuggingFaceProvider` class + agent definition with all tools
3. `prompt.py` — system instructions (viewport size, how to identify elements, etc.)
4. `logger.py` — colored timestamped console output

### Phase 4: Wire & Run

1. `main.py` — define task string, call `Runner.run()`
2. `python src/main.py` — watch it work

---

## Terminal Output

```
[17:05:32] 🟢 AGENT      Starting task...
[17:05:33] 🌐 BROWSER    Chromium launched (1280×720)
[17:05:34] 🔗 NAVIGATE   → https://ui.shadcn.com/docs/forms/react-hook-form
[17:05:37] 📷 SCREENSHOT  step_001.png
[17:05:39] 🧠 AI THINKS   → scroll(direction="down", amount=500)
[17:05:40] ⚡ EXECUTE     Scrolled down 500px
[17:05:42] 🧠 AI THINKS   → click_on_screen(x=640, y=385)
[17:05:43] ⚡ EXECUTE     Clicked at (640, 385)
[17:05:45] 🧠 AI THINKS   → send_keys(text="Linga Raghavendra")
[17:05:46] ⚡ EXECUTE     Typed "Linga Raghavendra"
...
[17:05:58] 🏁 DONE        Task completed
```

---

## Error Handling

| Problem | What Happens |
|---------|-------------|
| Click misses target | AI sees next screenshot, self-corrects |
| Form below the fold | AI calls `scroll` to find it |
| HF API rate limited | SDK retries automatically; add manual retry if needed |
| Tool throws error | Error string returned to AI, it adapts |
| Infinite loop | Set `max_turns` in RunConfig to cap iterations |
| Browser crashes | `try/finally` ensures `browser.close()` runs |

---

## Fallback: If Tool Calling Breaks

Some HF models have spotty function calling. If Qwen2.5-VL-7B's tool calling is flaky:

**Option A**: Switch model → `Qwen/Qwen2.5-VL-72B-Instruct` (better tool calling, still cheap)

**Option B**: Skip `@function_tool`, put tool definitions in the system prompt, ask model to return raw JSON, parse manually with `json.loads()`

---

## Dependencies (4 packages)

```
playwright>=1.52.0          # Browser control
openai>=4.90.0              # OpenAI-compatible client (talks to HuggingFace)
python-dotenv>=1.1.0        # Load .env file
Pillow>=11.0.0              # Screenshot compression (resize + JPEG)
```

> Note: We use `openai` SDK directly (not `openai-agents`) since we write our own loop for vision support. The `openai` package gives us `chat.completions.create()` with tool calling — that's all we need.

---

## Prerequisites

1. **Python 3.10+** — `python --version`
2. **HuggingFace account** — free at huggingface.co
3. **HF API token** — from https://huggingface.co/settings/tokens
4. **~200MB disk** — Chromium binary (one-time download)

---

*`python src/main.py` → browser opens → AI fills the form → done.*

 headless=False