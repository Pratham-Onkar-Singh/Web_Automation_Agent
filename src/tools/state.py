"""
src/tools/state.py
------------------
Shared mutable state container for the browser session.
"""

class BrowserState:
    """
    A plain data container that holds the live Playwright objects for
    the current browser session.
    """
    def __init__(self) -> None:
        self.playwright = None
        self.browser = None
        self.page = None
        self.step_count: int = 0

state = BrowserState()
