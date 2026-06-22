"""
src/tools/scroll.py
-------------------
Page scrolling tool for the Web Automation Agent.
"""

from src.tools.state import state
from src.utils.logger import logger

async def scroll(direction: str = None, target_y: int = None, amount: int = None) -> str:
    """
    Scroll the active browser page up or down, or center a specific element.
    """
    try:
        if not state.page:
            return "Error: Browser not open"
            
        if target_y is not None:
            amount_to_scroll = target_y - 360
            if amount_to_scroll == 0:
                return "Target is already centered"
            
            direction_str = "down" if amount_to_scroll > 0 else "up"
            logger.info(f"Centering target at y={target_y} by scrolling {direction_str} {abs(amount_to_scroll)}px")
            await state.page.mouse.wheel(0, amount_to_scroll)
            await state.page.wait_for_timeout(500)
            return f"Scrolled to center target originally at y={target_y}"
            
        elif direction:
            scroll_amount = amount if amount is not None else 500
            logger.info(f"Scrolling {direction} by {scroll_amount}px")
            
            if direction.lower() == "down":
                await state.page.mouse.wheel(0, scroll_amount)
            elif direction.lower() == "up":
                await state.page.mouse.wheel(0, -scroll_amount)
            else:
                return f"Error: Unknown scroll direction '{direction}'. Use 'up' or 'down'."
                
            await state.page.wait_for_timeout(500)
            return f"Scrolled {direction} by {scroll_amount}px"
            
        else:
            return "Error: Must provide either 'direction' or 'target_y' to scroll."
            
    except Exception as e:
        logger.error(f"Scroll failed: {e}")
        return f"Error: Scroll failed: {e}"
