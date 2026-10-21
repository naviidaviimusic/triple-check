"""Triple-Check Protocol: Python does the math, local LLMs explain it, a
different model family verifies every number."""

from .cell import Cell, Expert, format_report, format_verification
from .facts import FactBase

__all__ = ["Cell", "Expert", "FactBase", "format_report", "format_verification"]
__version__ = "0.1.0"
