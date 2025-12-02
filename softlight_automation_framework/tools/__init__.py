"""Tool/Action system for browser automation."""

from softlight_automation_framework.tools.registry import ToolRegistry, action
from softlight_automation_framework.tools.actions import (
    register_default_actions,
    NavigateAction,
    ClickAction,
    InputAction,
    ScrollAction,
    WaitAction,
    ExtractAction,
    ScreenshotAction,
    DoneAction,
    SendKeysAction,
    GoBackAction,
    SwitchTabAction,
    CloseTabAction,
)
from softlight_automation_framework.tools.views import (
    ActionResult,
    ActionModel,
    ActionDefinition,
)

__all__ = [
    "ToolRegistry",
    "action",
    "register_default_actions",
    "NavigateAction",
    "ClickAction",
    "InputAction",
    "ScrollAction",
    "WaitAction",
    "ExtractAction",
    "ScreenshotAction",
    "DoneAction",
    "SendKeysAction",
    "GoBackAction",
    "SwitchTabAction",
    "CloseTabAction",
    "ActionResult",
    "ActionModel",
    "ActionDefinition",
]

