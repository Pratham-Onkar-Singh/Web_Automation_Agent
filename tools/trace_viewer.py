"""Escape-safe, dependency-free JSONL trace viewer."""
import html
import json
import sys
from pathlib import Path


def render(path: str) -> str:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(f"<pre>{html.escape(json.dumps(json.loads(line), indent=2))}</pre>")
    return "<!doctype html><meta charset='utf-8'><title>Agent trace</title>" + "".join(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools/trace_viewer.py traces/episode.jsonl")
    print(render(sys.argv[1]))
