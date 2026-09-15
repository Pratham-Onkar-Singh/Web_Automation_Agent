"""
Entry point for the Web Automation Agent.
"""

import asyncio
from src.agent.agent import run_agent
from src.utils.logger import logger

TASK = """
Open youtube and search for Fifa highlights.
"""

async def main():
    try:
        await run_agent(TASK, protect_enter=False)
    except Exception as e:
        logger.error(f"Agent crashed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
