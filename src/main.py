"""
Entry point for the Web Automation Agent.
"""

import asyncio
from src.agent.agent import run_agent
from src.utils.logger import logger

TASK = """
1. You are on Youtube page
2. Search for Fifa highlights 
"""

START_URL = "https://www.youtube.com/"

async def main():
    try:
        await run_agent(TASK, START_URL)
    except Exception as e:
        logger.error(f"Agent crashed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
