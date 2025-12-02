"""
Browser Automation Framework
============================

A comprehensive multi-agent browser automation framework built using OpenAI GPT API 
and Playwright/CDP for autonomous web interaction.

Main Components:
- Agent: The main orchestrator for browser automation tasks
- BrowserSession: Manages browser instances and sessions
- ToolRegistry: Registry for browser actions and tools
- OpenAIClient: LLM integration for decision making

Quick Start:
    >>> from softlight_automation_framework import Agent, BrowserSession
    >>> from softlight_automation_framework.llm import OpenAIClient
    >>> 
    >>> async def main():
    ...     llm = OpenAIClient(model="gpt-4o")
    ...     async with BrowserSession() as browser:
    ...         agent = Agent(task="Your task", llm=llm, browser=browser)
    ...         result = await agent.run()
    ...     return result
"""

__version__ = "1.0.0"
__author__ = "Browser Automation Team"

# Lazy imports for better performance
_LAZY_IMPORTS = {
    "Agent": ("softlight_automation_framework.agent.executor", "Agent"),
    "BrowserSession": ("softlight_automation_framework.browser.session", "BrowserSession"),
    "BrowserDriver": ("softlight_automation_framework.browser.driver", "BrowserDriver"),
    "ToolRegistry": ("softlight_automation_framework.tools.registry", "ToolRegistry"),
    "ActionResult": ("softlight_automation_framework.tools.views", "ActionResult"),
    "DOMExtractor": ("softlight_automation_framework.dom.extractor", "DOMExtractor"),
    "OpenAIClient": ("softlight_automation_framework.llm.openai_client", "OpenAIClient"),
    "Config": ("softlight_automation_framework.core.config", "Config"),
    # Tutorial system
    "TutorialAgent": ("softlight_automation_framework.tutorial.agent", "TutorialAgent"),
    "WorkflowCapture": ("softlight_automation_framework.tutorial.capture", "WorkflowCapture"),
    "run_tutorial": ("softlight_automation_framework.tutorial.agent", "run_tutorial"),
}


def __getattr__(name: str):
    """Lazy import mechanism for main components."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        from importlib import import_module
        module = import_module(module_path)
        attr = getattr(module, attr_name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "Agent",
    "BrowserSession",
    "BrowserDriver", 
    "ToolRegistry",
    "ActionResult",
    "DOMExtractor",
    "OpenAIClient",
    "Config",
    # Tutorial system
    "TutorialAgent",
    "WorkflowCapture",
    "run_tutorial",
    "__version__",
]

