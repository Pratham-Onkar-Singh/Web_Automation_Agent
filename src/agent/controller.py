"""Single execution boundary for every browser side effect."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from src.agent.actions import ActionKind, ActionRequest, ScreenshotMeta, scale_action
from src.agent.policy import ActionPolicy, PolicyDenied
from src.tools.browser import navigate_to_url
from src.tools.keyboard import press_key, send_keys
from src.tools.mouse import click_on_screen, double_click
from src.tools.scroll import scroll
from src.tools.state import state
from src.tools.wait import wait


@dataclass
class ControllerResult:
    ok: bool
    message: str
    policy_denied: bool = False


class ActionController:
    def __init__(self, policy: ActionPolicy, max_actions: int = 25, *, protect_enter: bool = False):
        self.policy = policy
        self.max_actions = max_actions
        # This is trusted task configuration, never taken from model output.
        # General tasks such as search should be able to press Enter normally.
        self.protect_enter = protect_enter
        self.actions = 0

    async def execute(self, action: ActionRequest, meta: ScreenshotMeta, approval: str | None = None) -> ControllerResult:
        if self.actions >= self.max_actions:
            return ControllerResult(False, "action budget exhausted")
        try:
            action.validate(meta=meta)
            current_url = state.page.url if state.page else ""
            if action.kind is ActionKind.NAVIGATE:
                self.policy.check_url(action.args["url"])
            target = str(action.args.get("target", ""))
            protected = self.policy.is_protected(target)
            if self.protect_enter and action.kind is ActionKind.KEY and str(action.args.get("key", "")).lower() in {"enter", "control+enter", "meta+enter"}:
                protected = True
            if protected:
                if not approval:
                    raise PolicyDenied("protected action requires explicit approval")
                self.policy.consume_approval(approval, f"{action.kind.value}:{self.actions}", current_url, target)
            scaled = scale_action(action, meta)
            self.actions += 1
            result = await self._dispatch(scaled)
            return ControllerResult(not result.startswith("Error"), result)
        except PolicyDenied as exc:
            return ControllerResult(False, f"Policy denied: {exc}", True)
        except Exception as exc:
            return ControllerResult(False, f"Controller error: {exc}")

    async def _dispatch(self, action: ActionRequest) -> str:
        a = action.args
        if action.kind is ActionKind.CLICK:
            return await click_on_screen(int(a["x"]), int(a["y"]))
        if action.kind is ActionKind.DOUBLE_CLICK:
            return await double_click(int(a["x"]), int(a["y"]))
        if action.kind is ActionKind.TYPE:
            return await send_keys(a["text"])
        if action.kind is ActionKind.KEY:
            return await press_key(a["key"])
        if action.kind is ActionKind.SCROLL:
            return await scroll(a.get("direction"), a.get("target_y"), a.get("amount"))
        if action.kind is ActionKind.WAIT:
            return await wait(a["seconds"])
        if action.kind is ActionKind.NAVIGATE:
            return await navigate_to_url(a["url"])
        return "Done requested"
