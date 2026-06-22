"""
src/tools/mouse.py
------------------
Mouse interaction tools for the Web Automation Agent.
"""

from src.tools.state import state
from src.utils.logger import logger

async def click_on_screen(x: int, y: int) -> str:
    """
    Perform a single left-click at the given viewport coordinates.
    """
    try:
        if not state.page:
            return "Error: Browser not open"
            
        logger.info(f"Clicking at ({x}, {y})")
        await state.page.mouse.click(x, y)
        
        return f"Clicked at ({x}, {y})"
    except Exception as e:
        logger.error(f"Click failed: {e}")
        return f"Error: Click failed: {e}"

async def double_click(x: int, y: int) -> str:
    """
    Perform a double-click at the given viewport coordinates.
    """
    try:
        if not state.page:
            return "Error: Browser not open"
            
        logger.info(f"Double clicking at ({x}, {y})")
        await state.page.mouse.dblclick(x, y)
        
        return f"Double clicked at ({x}, {y})"
    except Exception as e:
        logger.error(f"Double click failed: {e}")
        return f"Error: Double click failed: {e}"
