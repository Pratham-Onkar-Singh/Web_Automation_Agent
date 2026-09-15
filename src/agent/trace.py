"""Sanitized JSONL episode traces. Page/model text is data, never markup."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET = re.compile(r"(?i)(hf_[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9_-]{8,}|bearer\s+[A-Za-z0-9._-]+)")


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return SECRET.sub("[REDACTED]", value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class TraceRecorder:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, event: str, **data: Any) -> None:
        row = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **redact(data)}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
