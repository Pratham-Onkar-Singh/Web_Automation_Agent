"""
src/tools/browser.py
--------------------
High-level browser lifecycle management for the Web Automation Agent.
"""

from playwright.async_api import async_playwright
from src.tools.state import state
from src.utils.logger import logger

async def open_browser() -> str:
    """
    Launch a visible Chromium browser at 1280x720 and store the handles.
    """
    try:
        if state.browser:
            return "Browser already open"
            
        logger.info("Launching Chromium (1280x720, visible)...")
        state.playwright = await async_playwright().start()
        state.browser = await state.playwright.chromium.launch(headless=False)
        state.page = await state.browser.new_page(viewport={"width": 1280, "height": 720})
        
        async def on_page(new_page):
            logger.info("New tab detected! Switching agent focus to new tab.")
            await new_page.bring_to_front()
            await new_page.wait_for_load_state("domcontentloaded")
            state.page = new_page
            
        state.browser.contexts[0].on("page", on_page)
        
        return "Browser launched successfully"
    except Exception as e:
        logger.error(f"Failed to open browser: {e}")
        return f"Error: Failed to open browser: {e}"

async def navigate_to_url(url: str) -> str:
    """
    Navigate the current browser tab to the given URL and wait until the network is idle.
    """
    try:
        if not state.page:
            return "Error: Browser not open"
            
        logger.info(f"Navigating to {url}")
        await state.page.goto(url, timeout=60000)
        
        try:
            await state.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            logger.info("networkidle timeout reached, continuing anyway...")
            
        return f"Navigated to {url}"
    except Exception as e:
        logger.error(f"Navigation to {url} failed: {e}")
        return f"Error: Navigation to {url} failed: {e}"

async def close_browser() -> str:
    """
    Tear down the browser and Playwright runtime in the correct order.
    """
    try:
        if state.browser:
            await state.browser.close()
            state.browser = None
            
        if state.playwright:
            await state.playwright.stop()
            state.playwright = None
            
        state.page = None
        logger.info("Browser closed")
        
        return "Browser closed"
    except Exception as e:
        logger.error(f"Failed to close browser: {e}")
        return f"Error: Failed to close browser: {e}"
