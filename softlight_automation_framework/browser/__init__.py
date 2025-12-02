"""Browser automation module - Playwright driver, sessions, and events."""

from softlight_automation_framework.browser.driver import BrowserDriver
from softlight_automation_framework.browser.session import BrowserSession
from softlight_automation_framework.browser.events import (
    BrowserEventBus,
    BrowserEvent,
    NavigationEvent,
    ClickEvent,
    TypeEvent,
    ScrollEvent,
)
from softlight_automation_framework.browser.views import (
    BrowserState,
    TabInfo,
    PageInfo,
    ViewportInfo,
)

__all__ = [
    "BrowserDriver",
    "BrowserSession",
    "BrowserEventBus",
    "BrowserEvent",
    "NavigationEvent",
    "ClickEvent", 
    "TypeEvent",
    "ScrollEvent",
    "BrowserState",
    "TabInfo",
    "PageInfo",
    "ViewportInfo",
]

