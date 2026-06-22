"""
Centralised configuration loader for the Web Automation Agent.
"""

import os

from dotenv import load_dotenv

load_dotenv()

HF_API_TOKEN: str | None = os.getenv("HF_API_TOKEN")

if not HF_API_TOKEN:
    print(
        "[Warning] HF_API_TOKEN not found in environment or .env file. "
        "The agent will fail when it tries to call the HuggingFace API."
    )
