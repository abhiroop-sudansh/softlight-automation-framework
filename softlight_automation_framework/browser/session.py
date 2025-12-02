"""Browser session management with state tracking and event handling."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from softlight_automation_framework.core.config import BrowserConfig, Config
from softlight_automation_framework.core.exceptions import BrowserError, SessionExpiredError
from softlight_automation_framework.browser.driver import BrowserDriver
from softlight_automation_framework.browser.events import (
    BrowserEventBus,
    BrowserEvent,
    NavigationEvent,
    ClickEvent,
    TypeEvent,
    ScrollEvent,
    WaitEvent,
    TabSwitchEvent,
    TabCloseEvent,
    GoBackEvent,
    SendKeysEvent,
    EventLogger,
    EventType,
)
from softlight_automation_framework.browser.views import (
    BrowserState,
    BrowserStateHistory,
    InteractiveElement,
)

logger = logging.getLogger(__name__)


class BrowserSession:
    """
    High-level browser session manager.
    
    Provides:
    - State management and caching
    - Event-driven browser operations
    - Automatic cleanup and resource management
    - Screenshot and history tracking
    - Persistent session support (cookies, localStorage)
    """
    
    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        headless: bool = False,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: int = 30000,
        save_screenshots: bool = False,
        screenshots_dir: str = "./screenshots",
        session_file: Optional[str] = None,
    ):
        """
        Initialize a browser session.
        
        Args:
            config: Browser configuration (overrides other params)
            headless: Run browser in headless mode
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            timeout: Default timeout in milliseconds
            save_screenshots: Save screenshots to disk
            screenshots_dir: Directory for saved screenshots
        """
        if config:
            self.config = config
        else:
            self.config = BrowserConfig(
                headless=headless,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                timeout=timeout,
            )
        
        self.session_id = str(uuid4())[:8]
        self.save_screenshots = save_screenshots
        self.screenshots_dir = Path(screenshots_dir)
        self.session_file = session_file
        
        # Core components
        self._driver: Optional[BrowserDriver] = None
        self._event_bus = BrowserEventBus()
        self._event_logger = EventLogger(self._event_bus)
        
        # State tracking
        self._current_state: Optional[BrowserState] = None
        self._previous_state: Optional[BrowserState] = None
        self._state_history: List[BrowserStateHistory] = []
        self._selector_map: Dict[int, Dict[str, Any]] = {}
        
        # Session tracking
        self._is_active = False
        self._step_count = 0
        self._start_time: Optional[datetime] = None
        self._downloaded_files: List[str] = []
        
        # Register event handlers
        self._register_event_handlers()
    
    def _register_event_handlers(self) -> None:
        """Register handlers for browser events."""
        self._event_bus.subscribe(EventType.NAVIGATION, self._handle_navigation)
        self._event_bus.subscribe(EventType.CLICK, self._handle_click)
        self._event_bus.subscribe(EventType.TYPE, self._handle_type)
        self._event_bus.subscribe(EventType.SCROLL, self._handle_scroll)
        self._event_bus.subscribe(EventType.WAIT, self._handle_wait)
        self._event_bus.subscribe(EventType.TAB_SWITCH, self._handle_tab_switch)
        self._event_bus.subscribe(EventType.TAB_CLOSE, self._handle_tab_close)
        self._event_bus.subscribe(EventType.GO_BACK, self._handle_go_back)
        self._event_bus.subscribe(EventType.SEND_KEYS, self._handle_send_keys)
    
    async def _handle_navigation(self, event: NavigationEvent) -> Dict[str, Any]:
        """Handle navigation events."""
        try:
            if event.new_tab:
                await self._driver.new_tab(event.url)
            else:
                await self._driver.navigate(event.url, wait_until=event.wait_until)
            return {"url": event.url, "new_tab": event.new_tab}
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise
    
    async def _handle_click(self, event: ClickEvent) -> Dict[str, Any]:
        """Handle click events."""
        if event.index is not None:
            result = await self._driver.click_element(
                event.index,
                button=event.button,
                click_count=event.click_count,
                force=event.force
            )
            return result
        elif event.coordinate_x is not None and event.coordinate_y is not None:
            await self._driver.click_coordinates(
                event.coordinate_x,
                event.coordinate_y,
                button=event.button
            )
            return {"click_x": event.coordinate_x, "click_y": event.coordinate_y}
        return {}
    
    async def _handle_type(self, event: TypeEvent) -> None:
        """Handle type events."""
        await self._driver.type_text(
            event.index,
            event.text,
            clear=event.clear,
            delay=event.delay_ms
        )
        
        if event.submit:
            await self._driver.send_keys("Enter")
    
    async def _handle_scroll(self, event: ScrollEvent) -> None:
        """Handle scroll events."""
        await self._driver.scroll(
            direction=event.direction,
            amount=event.amount,
            element_index=event.index
        )
    
    async def _handle_wait(self, event: WaitEvent) -> None:
        """Handle wait events."""
        if event.selector:
            await self._driver.wait_for_selector(event.selector)
        elif event.text:
            # Wait for text to appear
            script = f"""
                () => {{
                    return document.body.innerText.includes('{event.text}');
                }}
            """
            start = datetime.now()
            while (datetime.now() - start).total_seconds() < event.seconds:
                if await self._driver.execute_script(script):
                    return
                await asyncio.sleep(0.1)
        else:
            await asyncio.sleep(event.seconds)
    
    async def _handle_tab_switch(self, event: TabSwitchEvent) -> str:
        """Handle tab switch events."""
        await self._driver.switch_tab(int(event.target_id))
        return event.target_id
    
    async def _handle_tab_close(self, event: TabCloseEvent) -> None:
        """Handle tab close events."""
        await self._driver.close_tab(int(event.target_id))
    
    async def _handle_go_back(self, event: GoBackEvent) -> None:
        """Handle go back events."""
        await self._driver.go_back()
    
    async def _handle_send_keys(self, event: SendKeysEvent) -> None:
        """Handle send keys events."""
        await self._driver.send_keys(event.keys)
    
    async def start(self) -> "BrowserSession":
        """Start the browser session."""
        if self._is_active:
            logger.warning("Session already active")
            return self
        
        logger.info(f"Starting browser session {self.session_id}")
        
        self._driver = BrowserDriver(self.config, session_file=self.session_file)
        await self._driver.launch()
        
        self._is_active = True
        self._start_time = datetime.now()
        
        # Create screenshots directory if needed
        if self.save_screenshots:
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        return self
    
    async def stop(self) -> None:
        """Stop the browser session."""
        if not self._is_active:
            return
        
        logger.info(f"Stopping browser session {self.session_id}")
        
        if self._driver:
            await self._driver.close()
            self._driver = None
        
        self._is_active = False
        self._event_bus.clear_handlers()
    
    async def __aenter__(self) -> "BrowserSession":
        """Async context manager entry."""
        return await self.start()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
    
    def _ensure_active(self) -> None:
        """Ensure the session is active."""
        if not self._is_active or not self._driver:
            raise SessionExpiredError(self.session_id)
    
    @property
    def event_bus(self) -> BrowserEventBus:
        """Get the event bus."""
        return self._event_bus
    
    @property
    def driver(self) -> BrowserDriver:
        """Get the browser driver."""
        self._ensure_active()
        return self._driver
    
    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self._is_active
    
    @property
    def current_url(self) -> str:
        """Get current page URL."""
        if self._current_state:
            return self._current_state.url
        return ""
    
    @property
    def current_state(self) -> Optional[BrowserState]:
        """Get the current browser state."""
        return self._current_state
    
    @property
    def selector_map(self) -> Dict[int, Dict[str, Any]]:
        """Get the current selector map."""
        return self._selector_map
    
    @property
    def downloaded_files(self) -> List[str]:
        """Get list of downloaded files."""
        return self._downloaded_files.copy()
    
    async def get_state(self, force_refresh: bool = False) -> BrowserState:
        """
        Get the current browser state.
        
        Args:
            force_refresh: Force refresh even if cached state exists
            
        Returns:
            Current browser state
        """
        self._ensure_active()
        
        if not force_refresh and self._current_state:
            return self._current_state
        
        # Get fresh state from driver
        state = await self._driver.get_browser_state()
        
        # Mark new elements
        if self._previous_state:
            state.mark_new_elements(self._previous_state)
        
        # Update selector map
        _, self._selector_map = await self._driver.get_interactive_elements()
        
        # Update state tracking
        self._previous_state = self._current_state
        self._current_state = state
        
        # Save screenshot if enabled
        if self.save_screenshots:
            screenshot_path = self.screenshots_dir / f"step_{self._step_count:03d}.png"
            if state.screenshot_b64:
                import base64
                screenshot_path.write_bytes(base64.b64decode(state.screenshot_b64))
                state.screenshot_path = str(screenshot_path)
        
        # Add to history
        self._state_history.append(BrowserStateHistory(
            url=state.url,
            title=state.title,
            screenshot_b64=state.screenshot_b64,
            screenshot_path=state.screenshot_path,
        ))
        
        return state
    
    async def get_element_by_index(self, index: int) -> Optional[InteractiveElement]:
        """Get an interactive element by its index."""
        if self._current_state:
            return self._current_state.get_element_by_index(index)
        return None
    
    async def get_selector_map(self) -> Dict[int, Dict[str, Any]]:
        """Get the selector map for element interactions."""
        if not self._selector_map:
            await self.get_state(force_refresh=True)
        return self._selector_map
    
    # High-level action methods
    
    async def navigate(self, url: str, new_tab: bool = False) -> None:
        """Navigate to a URL."""
        event = NavigationEvent(url=url, new_tab=new_tab)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
        self._step_count += 1
    
    async def click(
        self,
        index: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> Dict[str, Any]:
        """Click on an element or coordinates."""
        event = ClickEvent(index=index, coordinate_x=x, coordinate_y=y)
        await self._event_bus.dispatch(event)
        result = await event.wait_for_result()
        self._step_count += 1
        return result or {}
    
    async def type_text(
        self,
        index: int,
        text: str,
        clear: bool = True,
        submit: bool = False
    ) -> None:
        """Type text into an element."""
        event = TypeEvent(index=index, text=text, clear=clear, submit=submit)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
        self._step_count += 1
    
    async def scroll(
        self,
        direction: str = "down",
        pages: float = 1.0,
        element_index: Optional[int] = None
    ) -> None:
        """Scroll the page or an element."""
        viewport = await self._driver.get_viewport_size()
        amount = int(pages * viewport["height"])
        
        event = ScrollEvent(direction=direction, amount=amount, index=element_index)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
    
    async def wait(self, seconds: float = 1.0) -> None:
        """Wait for a specified time."""
        event = WaitEvent(seconds=seconds)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
    
    async def go_back(self) -> None:
        """Navigate back in history."""
        event = GoBackEvent()
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
        self._step_count += 1
    
    async def send_keys(self, keys: str) -> None:
        """Send keyboard keys."""
        event = SendKeysEvent(keys=keys)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
    
    async def switch_tab(self, tab_id: str) -> None:
        """Switch to a different tab."""
        event = TabSwitchEvent(target_id=tab_id)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
    
    async def close_tab(self, tab_id: str) -> None:
        """Close a tab."""
        event = TabCloseEvent(target_id=tab_id)
        await self._event_bus.dispatch(event)
        await event.wait_for_result()
    
    async def screenshot(self, full_page: bool = False) -> str:
        """Take a screenshot and return as base64."""
        self._ensure_active()
        return await self._driver.screenshot(full_page=full_page)
    
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in the page."""
        self._ensure_active()
        return await self._driver.execute_script(script)
    
    async def extract_content(self, query: str) -> str:
        """
        Extract content from the page based on a query.
        
        This is a simple extraction - for full LLM-based extraction,
        use the Agent's extract action.
        """
        self._ensure_active()
        
        # Get page text content
        content = await self._driver.execute_script("""
            () => {
                // Remove script and style elements
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                return clone.innerText;
            }
        """)
        
        return content
    
    def get_history(self) -> List[BrowserStateHistory]:
        """Get the state history."""
        return self._state_history.copy()
    
    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get the event log."""
        return self._event_logger.get_events()
    
    async def highlight_element(
        self,
        index: int,
        color: str = "rgba(255, 0, 0, 0.3)",
        duration_ms: int = 1000
    ) -> None:
        """Highlight an element for debugging."""
        self._ensure_active()
        await self._driver.highlight_element(index, color, duration_ms)


@asynccontextmanager
async def create_session(**kwargs) -> BrowserSession:
    """
    Context manager for creating browser sessions.
    
    Usage:
        async with create_session(headless=False) as session:
            await session.navigate("https://example.com")
    """
    session = BrowserSession(**kwargs)
    try:
        yield await session.start()
    finally:
        await session.stop()

