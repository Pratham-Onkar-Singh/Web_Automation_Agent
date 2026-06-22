"""
Lightweight logger for the Web Automation Agent.
"""

import sys
from datetime import datetime


class Logger:
    """A minimal logger that writes timestamped messages to stdout and stderr."""

    def info(self, msg: str) -> None:
        """Log an informational message to stdout."""
        try:
            time_str = datetime.now().strftime("%H:%M:%S")
            print(f"[{time_str}] 🟢 {msg}", flush=True)
        except Exception as e:
            print(f"Failed to log info: {e}")

    def error(self, msg: str) -> None:
        """Log an error message to stderr."""
        try:
            time_str = datetime.now().strftime("%H:%M:%S")
            print(f"[{time_str}] 🔴 ERROR: {msg}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"Failed to log error: {e}", file=sys.stderr)


logger = Logger()
