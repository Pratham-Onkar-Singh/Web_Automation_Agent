"""Screenshot-driven perception/decision/action loop."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from openai import AsyncOpenAI

from src.agent.actions import ActionKind, ActionRequest, ScreenshotMeta
from src.agent.controller import ActionController
from src.agent.policy import ActionPolicy
from src.agent.prompt import SYSTEM_PROMPT
from src.agent.recorded import RecordedResponseAdapter
from src.agent.trace import TraceRecorder
from src.agent.verification import Ending, verify_done
from src.tools.browser import close_browser, navigate_to_url, open_browser
from src.tools.screenshot import take_screenshot
from src.tools.state import state
from src.utils.config import HF_API_TOKEN, MODEL
from src.utils.logger import logger

INVALID_ACTION_LIMIT = 3


def extract_json(content: str) -> dict[str, Any]:
    """Extract the first balanced JSON object from model prose."""
    for match in re.finditer(r"\{", content):
        start = match.start()
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(content)):
            char = content[index]
            if escaped:
                escaped = False
                continue
            if char == "\\" and in_string:
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(content[start:index + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
    raise ValueError("model response contained no valid JSON object")


def sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(args)
    for key in ("x", "y", "target_y", "amount", "seconds"):
        if isinstance(cleaned.get(key), list) and len(cleaned[key]) == 1:
            cleaned[key] = cleaned[key][0]
        if isinstance(cleaned.get(key), str):
            try:
                cleaned[key] = int(cleaned[key])
            except ValueError:
                pass
    return cleaned


def parse_action(raw: dict[str, Any], meta: ScreenshotMeta) -> ActionRequest:
    """Parse current pixel coordinates, with a bounded legacy compatibility shim."""
    raw = dict(raw)
    raw["args"] = sanitize_args(raw.get("args", {}))
    try:
        return ActionRequest.from_dict(raw, meta=meta)
    except Exception:
        # Earlier prompt versions used normalized 0–1000 coordinates. Only
        # reinterpret values that fail the current pixel bounds and are within
        # that old range; all other invalid values remain rejected.
        kind = str(raw.get("tool", "")).strip().lower()
        args = dict(raw["args"])
        if kind in {ActionKind.CLICK.value, ActionKind.DOUBLE_CLICK.value}:
            x, y = args.get("x"), args.get("y")
            if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (x, y)) and 0 <= x <= 1000 and 0 <= y <= 1000 and (x > meta.width or y > meta.height):
                args["x"] = round(x * meta.viewport_width / 1000)
                args["y"] = round(y * meta.viewport_height / 1000)
                raw["args"] = args
                return ActionRequest.from_dict(raw, meta=meta)
        raise


async def run_agent(task: str, start_url: str | None = None, *, response_adapter: RecordedResponseAdapter | None = None,
                    completion_predicate=None, allowed_origins: set[str] | None = None,
                    max_steps: int = 25, trace_path: str | Path = "traces/episode.jsonl",
                    protect_enter: bool = False) -> Ending:
    logger.info("Starting Agent...")
    parsed = urlsplit(start_url) if start_url else None
    origins = allowed_origins or ({f"{parsed.scheme}://{parsed.netloc}"} if parsed else None)
    policy = ActionPolicy(origins, allow_bootstrap_navigation=origins is None)
    controller = ActionController(policy, max_steps, protect_enter=protect_enter)
    trace = TraceRecorder(trace_path)
    client = None if response_adapter else AsyncOpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_API_TOKEN)
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Task: {task}"}]
    ending = Ending.BUDGET_EXHAUSTED
    invalid_action_count = 0
    try:
        await open_browser(origins)
        if start_url:
            if (nav := await navigate_to_url(start_url)).startswith("Error"):
                return Ending.BROWSER_ERROR
        for step in range(max_steps):
            if not state.page or state.page.is_closed():
                ending = Ending.BROWSER_ERROR
                break
            screenshot = await take_screenshot()
            meta: ScreenshotMeta = state.screenshot_meta
            messages.append({"role": "user", "content": [{"type": "text", "text": f"Current screenshot is {meta.width}x{meta.height}. Return one JSON action."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot}"}}]})
            trace.event("observation", step=step + 1, screenshot=f"step_{step + 1:03d}.png", viewport=meta.__dict__)
            try:
                if response_adapter:
                    content = await response_adapter.complete(messages)
                else:
                    response = await client.chat.completions.create(model=MODEL, messages=messages)  # type: ignore[union-attr]
                    content = response.choices[0].message.content or ""
            except Exception as exc:
                trace.event("ending", ending=Ending.PROVIDER_ERROR.value, reason=str(exc))
                ending = Ending.PROVIDER_ERROR
                break
            messages.append({"role": "assistant", "content": content})
            try:
                raw = extract_json(content)
                action = parse_action(raw, meta)
            except Exception as exc:
                invalid_action_count += 1
                trace.event("policy", decision="deny", reason=f"invalid_action: {exc}")
                if invalid_action_count >= INVALID_ACTION_LIMIT:
                    ending = Ending.INVALID_MODEL_OUTPUT
                    trace.event("ending", ending=ending.value, reason="three consecutive invalid model actions")
                    break
                messages.append({"role": "user", "content": f"Invalid action: {exc}. Return valid JSON."})
                continue
            invalid_action_count = 0
            trace_args = dict(action.args)
            if "text" in trace_args:
                trace_args["text"] = "[REDACTED]"
            trace.event("proposed_action", step=step + 1, action=action.kind.value, args=trace_args)
            if action.kind.value == "done":
                verification = await verify_done(completion_predicate)
                trace.event("ending", ending=verification.ending.value, reason=verification.reason)
                ending = verification.ending
                break
            result = await controller.execute(action, meta)
            trace.event("action_result", action=action.kind.value, ok=result.ok, result=result.message)
            if result.policy_denied:
                ending = Ending.POLICY_BLOCKED
                break
            messages.append({"role": "user", "content": f"Controller result: {result.message}"})
        else:
            trace.event("ending", ending=ending.value, reason="step budget exhausted")
    finally:
        await close_browser()
        logger.info(f"Finished: {ending.value}")
    return ending
