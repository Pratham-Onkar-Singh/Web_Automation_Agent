"""
src/tools/screenshot.py
-----------------------
Screenshot capture and compression for the Web Automation Agent.
"""

import base64
import io
import os
from PIL import Image

from src.tools.state import state
from src.utils.logger import logger

async def take_screenshot() -> str:
    """
    Capture the current browser viewport, persist a full-resolution PNG
    to disk, and return a compressed JPEG as a base64-encoded string.
    """
    if not state.page:
        raise RuntimeError("Browser page not initialized")
        
    state.step_count += 1
    filename = f"screenshots/step_{state.step_count:03d}.png"
    
    os.makedirs('screenshots', exist_ok=True)
    png_bytes = await state.page.screenshot(path=filename)
    logger.info(f"Screenshot saved to {filename}")
    
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
