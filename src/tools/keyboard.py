"""
src/tools/keyboard.py
---------------------
Keyboard input tool for the Web Automation Agent.
"""

from src.tools.state import state
from src.utils.logger import logger

async def send_keys(text: str) -> str:
    """
    Type text into the currently focused element.
    """
    try:
        if not state.page:
            return "Error: Browser not open"
            
        logger.info(f"Typing: {text}")
        await state.page.keyboard.type(text)
        return f"Typed: {text}"
    except Exception as e:
        logger.error(f"Type failed: {e}")
        return f"Error: Type failed: {e}"

async def press_key(key: str) -> str:
    """
    Press a specific key on the keyboard (e.g., 'Enter', 'Escape', 'Tab', 'Backspace').
    """
    try:
        if not state.page:
            return "Error: Browser not open"
            
        logger.info(f"Pressing key: {key}")
        await state.page.keyboard.press(key)
        return f"Pressed key: {key}"
    except Exception as e:
        logger.error(f"Key press failed: {e}")
        return f"Error: Key press failed: {e}"
