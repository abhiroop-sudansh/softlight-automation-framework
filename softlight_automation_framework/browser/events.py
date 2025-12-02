"""Browser event system for handling async browser operations."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of browser events."""
    NAVIGATION = "navigation"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    TAB_SWITCH = "tab_switch"
    TAB_CLOSE = "tab_close"
    GO_BACK = "go_back"
    UPLOAD = "upload"
    DROPDOWN = "dropdown"
    SEND_KEYS = "send_keys"


@dataclass
class BrowserEvent(ABC):
    """Base class for browser events."""
    
    event_type: EventType = field(init=False)
    timestamp: datetime = field(default_factory=datetime.now)
    _result: Any = field(default=None, init=False)
    _exception: Optional[Exception] = field(default=None, init=False)
    _completed: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    
    def set_result(self, result: Any) -> None:
        """Set the event result and mark as completed."""
        self._result = result
        self._completed.set()
    
    def set_exception(self, exception: Exception) -> None:
        """Set an exception and mark as completed."""
        self._exception = exception
        self._completed.set()
    
    async def wait_for_result(
        self,
        timeout: float = 30.0,
        raise_on_error: bool = True
    ) -> Any:
        """Wait for the event to complete and return the result."""
        try:
            await asyncio.wait_for(self._completed.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Event {self.event_type} timed out after {timeout}s")
        
        if self._exception and raise_on_error:
            raise self._exception
        
        return self._result


@dataclass
class NavigationEvent(BrowserEvent):
    """Navigate to a URL."""
    
    url: str = ""
    new_tab: bool = False
    wait_until: str = "domcontentloaded"
    
    def __post_init__(self):
        self.event_type = EventType.NAVIGATION


@dataclass
class ClickEvent(BrowserEvent):
    """Click on an element."""
    
    index: Optional[int] = None
    coordinate_x: Optional[int] = None
    coordinate_y: Optional[int] = None
    button: str = "left"
    click_count: int = 1
    force: bool = False
    
    def __post_init__(self):
        self.event_type = EventType.CLICK


@dataclass
class TypeEvent(BrowserEvent):
    """Type text into an element."""
    
    index: int = 0
    text: str = ""
    clear: bool = True
    submit: bool = False
    delay_ms: int = 0
    
    def __post_init__(self):
        self.event_type = EventType.TYPE


@dataclass
class ScrollEvent(BrowserEvent):
    """Scroll the page or an element."""
    
    direction: str = "down"  # up, down, left, right
    amount: int = 0  # pixels or 0 for viewport height
    index: Optional[int] = None  # element to scroll, None for page
    
    def __post_init__(self):
        self.event_type = EventType.SCROLL


@dataclass
class WaitEvent(BrowserEvent):
    """Wait for a condition or time."""
    
    seconds: float = 1.0
    selector: Optional[str] = None
    text: Optional[str] = None
    
    def __post_init__(self):
        self.event_type = EventType.WAIT


@dataclass
class ScreenshotEvent(BrowserEvent):
    """Take a screenshot."""
    
    full_page: bool = False
    element_index: Optional[int] = None
    
    def __post_init__(self):
        self.event_type = EventType.SCREENSHOT


@dataclass
class TabSwitchEvent(BrowserEvent):
    """Switch to a different tab."""
    
    target_id: str = ""
    
    def __post_init__(self):
        self.event_type = EventType.TAB_SWITCH


@dataclass
class TabCloseEvent(BrowserEvent):
    """Close a tab."""
    
    target_id: str = ""
    
    def __post_init__(self):
        self.event_type = EventType.TAB_CLOSE


@dataclass
class GoBackEvent(BrowserEvent):
    """Navigate back in history."""
    
    def __post_init__(self):
        self.event_type = EventType.GO_BACK


@dataclass
class UploadFileEvent(BrowserEvent):
    """Upload a file to an input element."""
    
    index: int = 0
    file_path: str = ""
    
    def __post_init__(self):
        self.event_type = EventType.UPLOAD


@dataclass
class DropdownEvent(BrowserEvent):
    """Interact with a dropdown element."""
    
    index: int = 0
    value: Optional[str] = None
    get_options: bool = False
    
    def __post_init__(self):
        self.event_type = EventType.DROPDOWN


@dataclass
class SendKeysEvent(BrowserEvent):
    """Send keyboard keys."""
    
    keys: str = ""  # e.g., "Enter", "Tab Tab ArrowDown"
    
    def __post_init__(self):
        self.event_type = EventType.SEND_KEYS


EventHandler = Callable[[BrowserEvent], Any]


class BrowserEventBus:
    """Event bus for browser operations."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._pending_events: List[BrowserEvent] = []
    
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """Subscribe a handler to a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all events."""
        self._global_handlers.append(handler)
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
    
    async def dispatch(self, event: BrowserEvent) -> BrowserEvent:
        """
        Dispatch an event to all subscribed handlers.
        
        Returns the event with result set after handlers complete.
        """
        self._pending_events.append(event)
        
        try:
            # Call specific handlers
            handlers = self._handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        result = await result
                    
                    # Set result from first successful handler
                    if result is not None and event._result is None:
                        event.set_result(result)
                        
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
                    event.set_exception(e)
                    break
            
            # Call global handlers
            for handler in self._global_handlers:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.warning(f"Global event handler error: {e}")
            
            # Mark as completed if not already
            if not event._completed.is_set():
                event.set_result(None)
                
        finally:
            self._pending_events.remove(event)
        
        return event
    
    def dispatch_sync(self, event: BrowserEvent) -> BrowserEvent:
        """Dispatch an event synchronously (for use in sync contexts)."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a future and schedule the dispatch
            future = asyncio.ensure_future(self.dispatch(event))
            return event
        else:
            return loop.run_until_complete(self.dispatch(event))
    
    @property
    def pending_count(self) -> int:
        """Get number of pending events."""
        return len(self._pending_events)
    
    def clear_handlers(self) -> None:
        """Clear all event handlers."""
        self._handlers.clear()
        self._global_handlers.clear()


class EventLogger:
    """Logs browser events for debugging and tracing."""
    
    def __init__(self, event_bus: BrowserEventBus):
        self.event_bus = event_bus
        self.events: List[Dict[str, Any]] = []
        event_bus.subscribe_all(self._log_event)
    
    def _log_event(self, event: BrowserEvent) -> None:
        """Log an event."""
        event_data = {
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
        }
        
        # Add event-specific fields
        if isinstance(event, NavigationEvent):
            event_data["url"] = event.url
            event_data["new_tab"] = event.new_tab
        elif isinstance(event, ClickEvent):
            event_data["index"] = event.index
            event_data["coordinates"] = (event.coordinate_x, event.coordinate_y)
        elif isinstance(event, TypeEvent):
            event_data["index"] = event.index
            event_data["text_length"] = len(event.text)
        elif isinstance(event, ScrollEvent):
            event_data["direction"] = event.direction
            event_data["amount"] = event.amount
        
        self.events.append(event_data)
        logger.debug(f"Browser event: {event_data}")
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self.events.copy()
    
    def clear(self) -> None:
        """Clear logged events."""
        self.events.clear()

