"""
src/tools/wait.py
-----------------
Simple async wait tool for the Web Automation Agent.
"""

import asyncio
from src.utils.logger import logger

async def wait(seconds: int) -> str:
    """
    Pause execution for the given number of seconds.
    """
    try:
        seconds = min(int(seconds), 10)
        logger.info(f"Waiting {seconds} second(s)...")
        await asyncio.sleep(seconds)
        return f"Waited {seconds} second(s)"
    except Exception as e:
        logger.error(f"Wait failed: {e}")
        return f"Error: Wait failed: {e}"
