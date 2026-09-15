"""
Centralised configuration loader for the Web Automation Agent.
"""

import os

from dotenv import load_dotenv

load_dotenv()

HF_API_TOKEN: str | None = os.getenv("HF_API_TOKEN")
MODEL: str = os.getenv("WEB_AGENT_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct")

if not HF_API_TOKEN:
    print(
        "[Warning] HF_API_TOKEN not found in environment or .env file. "
        "The agent will fail when it tries to call the HuggingFace API."
    )
