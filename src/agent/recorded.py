"""Offline provider adapter used by tests and reproducible evaluations."""

from __future__ import annotations

import json
from pathlib import Path


class RecordedResponseAdapter:
    def __init__(self, responses: list[str] | list[dict] | str | Path):
        if isinstance(responses, (str, Path)) and Path(responses).exists():
            self.responses = [json.loads(line)["response"] for line in Path(responses).read_text().splitlines() if line.strip()]
        else:
            self.responses = list(responses)  # type: ignore[arg-type]
        self.index = 0

    async def complete(self, *_args, **_kwargs) -> str:
        if self.index >= len(self.responses):
            raise RuntimeError("recorded response adapter exhausted")
        response = self.responses[self.index]
        self.index += 1
        return response if isinstance(response, str) else json.dumps(response)
