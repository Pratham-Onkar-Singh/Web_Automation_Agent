"""Typed, bounded actions exchanged between the model and the controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionKind(str, Enum):
    CLICK = "click_on_screen"
    DOUBLE_CLICK = "double_click"
    TYPE = "send_keys"
    KEY = "press_key"
    SCROLL = "scroll"
    WAIT = "wait"
    NAVIGATE = "navigate_to_url"
    DONE = "done"


class ActionValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ScreenshotMeta:
    width: int
    height: int
    viewport_width: int
    viewport_height: int


@dataclass(frozen=True)
class ActionRequest:
    kind: ActionKind
    args: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, meta: ScreenshotMeta | None = None) -> "ActionRequest":
        if not isinstance(raw, dict):
            raise ActionValidationError("action must be an object")
        try:
            kind = ActionKind(str(raw.get("tool", "")).strip().lower())
        except ValueError as exc:
            raise ActionValidationError(f"unsupported tool: {raw.get('tool')!r}") from exc
        args = raw.get("args", {})
        if not isinstance(args, dict):
            raise ActionValidationError("args must be an object")
        action = cls(kind, dict(args), str(raw.get("reasoning", "")))
        action.validate(meta=meta)
        return action

    def validate(self, *, meta: ScreenshotMeta | None = None, max_text: int = 4000) -> None:
        a = self.args
        if self.kind in (ActionKind.CLICK, ActionKind.DOUBLE_CLICK):
            self._number(a, "x", 0, meta.width if meta else 1000)
            self._number(a, "y", 0, meta.height if meta else 1000)
        elif self.kind is ActionKind.TYPE:
            text = a.get("text")
            if not isinstance(text, str) or not text:
                raise ActionValidationError("text must be a non-empty string")
            if len(text) > max_text:
                raise ActionValidationError("text exceeds the configured limit")
        elif self.kind is ActionKind.KEY:
            key = a.get("key")
            if not isinstance(key, str) or not key or len(key) > 40:
                raise ActionValidationError("key must be a short non-empty string")
        elif self.kind is ActionKind.SCROLL:
            direction = a.get("direction")
            target_y = a.get("target_y")
            if direction not in (None, "up", "down") and target_y is None:
                raise ActionValidationError("direction must be up or down")
            if target_y is not None:
                self._number(a, "target_y", 0, meta.height if meta else 1000)
            if a.get("amount") is not None:
                self._number(a, "amount", 1, 4000)
        elif self.kind is ActionKind.WAIT:
            self._number(a, "seconds", 0, 10)
        elif self.kind is ActionKind.NAVIGATE:
            if not isinstance(a.get("url"), str) or not a["url"].strip():
                raise ActionValidationError("url must be a non-empty string")
        elif self.kind is ActionKind.DONE and a:
            raise ActionValidationError("done does not accept arguments")

    @staticmethod
    def _number(args: dict[str, Any], name: str, low: float, high: float) -> None:
        value = args.get(name)
        if isinstance(value, bool):
            raise ActionValidationError(f"{name} must be numeric")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ActionValidationError(f"{name} must be numeric") from exc
        if not low <= number <= high:
            raise ActionValidationError(f"{name} must be between {low:g} and {high:g}")


def scale_normalized(value: float, source: int, target: int) -> int:
    if source <= 0 or target <= 0:
        raise ValueError("dimensions must be positive")
    return round(float(value) * target / source)


def scale_action(action: ActionRequest, meta: ScreenshotMeta) -> ActionRequest:
    """Convert screenshot coordinates into the actual Playwright viewport."""
    args = dict(action.args)
    if action.kind in (ActionKind.CLICK, ActionKind.DOUBLE_CLICK):
        args["x"] = scale_normalized(args["x"], meta.width, meta.viewport_width)
        args["y"] = scale_normalized(args["y"], meta.height, meta.viewport_height)
    elif action.kind is ActionKind.SCROLL and args.get("target_y") is not None:
        args["target_y"] = scale_normalized(args["target_y"], meta.height, meta.viewport_height)
    return ActionRequest(action.kind, args, action.reasoning)
