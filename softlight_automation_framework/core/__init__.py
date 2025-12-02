"""Core framework components - configuration, logging, and exceptions."""

from softlight_automation_framework.core.config import Config
from softlight_automation_framework.core.exceptions import (
    BrowserAutomationError,
    BrowserError,
    AgentError,
    ActionError,
    DOMError,
    LLMError,
    TimeoutError as BrowserTimeoutError,
)
from softlight_automation_framework.core.logging import setup_logging, get_logger

__all__ = [
    "Config",
    "BrowserAutomationError",
    "BrowserError", 
    "AgentError",
    "ActionError",
    "DOMError",
    "LLMError",
    "BrowserTimeoutError",
    "setup_logging",
    "get_logger",
]

