"""Browser driver using Playwright for browser automation."""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    CDPSession,
    ElementHandle,
)

from softlight_automation_framework.core.config import BrowserConfig
from softlight_automation_framework.core.exceptions import (
    BrowserError,
    ElementNotFoundError,
    NavigationError,
    TimeoutError,
)
from softlight_automation_framework.browser.views import (
    BrowserState,
    InteractiveElement,
    TabInfo,
)

logger = logging.getLogger(__name__)


class BrowserDriver:
    """
    Low-level browser driver using Playwright and CDP.
    
    Handles direct browser interactions, DOM manipulation,
    and screenshot capture.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None, session_file: Optional[str] = None):
        self.config = config or BrowserConfig.from_env()
        self.session_file = session_file
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cdp_session: Optional[CDPSession] = None
        self._selector_map: Dict[int, Dict[str, Any]] = {}
    
    async def launch(self) -> None:
        """Launch the browser instance."""
        logger.info("Launching browser...")
        
        self._playwright = await async_playwright().start()
        
        launch_options = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo,
        }
        
        self._browser = await self._playwright.chromium.launch(**launch_options)
        
        context_options = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            "ignore_https_errors": self.config.ignore_https_errors,
        }
        
        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent
        
        # Load saved session if available
        if self.session_file and Path(self.session_file).exists():
            context_options["storage_state"] = self.session_file
            logger.info(f"Loading saved session from {self.session_file}")
        
        self._context = await self._browser.new_context(**context_options)
        self._page = await self._context.new_page()
        
        # Set up CDP session for advanced operations
        self._cdp_session = await self._page.context.new_cdp_session(self._page)
        
        # Enable DOM and accessibility
        await self._cdp_session.send("DOM.enable")
        await self._cdp_session.send("Accessibility.enable")
        
        logger.info(f"Browser launched (headless={self.config.headless})")
    
    async def close(self) -> None:
        """Close the browser instance."""
        logger.info("Closing browser...")
        
        if self._cdp_session:
            await self._cdp_session.detach()
            self._cdp_session = None
        
        if self._context:
            await self._context.close()
            self._context = None
        
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        logger.info("Browser closed")
    
    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise BrowserError("Browser not launched")
        return self._page
    
    @property
    def context(self) -> BrowserContext:
        """Get the browser context."""
        if not self._context:
            raise BrowserError("Browser not launched")
        return self._context
    
    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None
    ) -> None:
        """Navigate to a URL."""
        timeout = timeout or self.config.timeout
        
        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(
                url,
                wait_until=wait_until,
                timeout=timeout
            )
            logger.debug(f"Navigation complete: {url}")
        except Exception as e:
            raise NavigationError(f"Failed to navigate to {url}: {e}")
    
    async def go_back(self) -> None:
        """Navigate back in history."""
        try:
            await self.page.go_back()
            logger.debug("Navigated back")
        except Exception as e:
            raise NavigationError(f"Failed to go back: {e}")
    
    async def reload(self) -> None:
        """Reload the current page."""
        await self.page.reload()
        logger.debug("Page reloaded")
    
    async def get_url(self) -> str:
        """Get the current page URL."""
        return self.page.url
    
    async def get_title(self) -> str:
        """Get the current page title."""
        try:
            return await self.page.title()
        except Exception:
            # Handle execution context destroyed during navigation
            return ""
    
    async def screenshot(
        self,
        full_page: bool = False,
        path: Optional[str] = None
    ) -> str:
        """
        Take a screenshot and return as base64.
        
        Args:
            full_page: Capture full scrollable page
            path: Optional path to save screenshot
            
        Returns:
            Base64 encoded screenshot
        """
        screenshot_bytes = await self.page.screenshot(
            full_page=full_page,
            type="png"
        )
        
        if path:
            Path(path).write_bytes(screenshot_bytes)
            logger.debug(f"Screenshot saved: {path}")
        
        return base64.b64encode(screenshot_bytes).decode("utf-8")
    
    async def _wait_for_loading_overlays(self, timeout: float = 10.0) -> None:
        """
        Wait for common loading overlays to disappear.
        Handles GitHub's PJAX loader and similar loading indicators.
        """
        import asyncio
        
        # Common loading overlay selectors
        loading_selectors = [
            ".progress-pjax-loader",  # GitHub PJAX loader
            "span.progress-pjax-loader",  # GitHub specific span
            ".Progress.position-fixed",  # GitHub fixed progress bar
            ".pjax-loader",           # GitHub alternative
            "[data-pjax-container] .loading",
            ".turbo-progress-bar",    # Turbo/Hotwire
            ".nprogress",             # NProgress
            "[class*='loading-bar']",
            "[class*='progress-bar']:not([aria-valuenow='0'])",
        ]
        
        try:
            for selector in loading_selectors:
                try:
                    # Wait for loading element to be hidden or detached
                    locator = self.page.locator(selector)
                    count = await locator.count()
                    if count > 0:
                        await locator.first.wait_for(state="hidden", timeout=timeout * 1000)
                        logger.debug(f"Loading overlay '{selector}' finished")
                        # Small delay after loading completes
                        await asyncio.sleep(0.2)
                except Exception:
                    # Timeout or element not found - continue
                    pass
            
            # Extra safety: wait a bit for any CSS transitions
            await asyncio.sleep(0.1)
            
            # Small delay to ensure UI is stable
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.debug(f"Loading overlay wait skipped: {e}")
    
    async def click_element(
        self,
        index: int,
        button: str = "left",
        click_count: int = 1,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Click on an element by its index.
        
        Args:
            index: Element index from selector map
            button: Mouse button (left, right, middle)
            click_count: Number of clicks
            force: Force click even if element is obscured
            
        Returns:
            Click result with coordinates
        """
        import asyncio
        
        element_info = self._selector_map.get(index)
        if not element_info:
            raise ElementNotFoundError(
                f"index={index}",
                "Element not found in selector map"
            )
        
        async def _attempt_click(use_force: bool = False) -> Dict[str, Any]:
            """Attempt to click with optional force."""
            # Wait for loading overlays to disappear (GitHub, etc.)
            await self._wait_for_loading_overlays()
            
            # Use stored coordinates directly
            x = element_info.get("center_x")
            y = element_info.get("center_y")
            
            if x is not None and y is not None and not use_force:
                # Perform click at stored coordinates
                await self.page.mouse.click(
                    x, y,
                    button=button,
                    click_count=click_count
                )
                logger.debug(f"Clicked element {index} at ({x}, {y})")
                return {"click_x": x, "click_y": y}
            
            # Use XPath with force option
            xpath = element_info.get("xpath")
            if xpath:
                locator = self.page.locator(f"xpath={xpath}")
                await locator.click(button=button, click_count=click_count, force=use_force, timeout=10000)
                box = await locator.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    logger.debug(f"Clicked element {index} via xpath at ({x}, {y}) [force={use_force}]")
                    return {"click_x": x, "click_y": y}
            
            raise BrowserError(f"Could not find element {index}")
        
        try:
            # First attempt without force
            return await _attempt_click(use_force=force)
            
        except Exception as first_error:
            # Check if it's an interception error
            error_str = str(first_error).lower()
            if "intercept" in error_str or "timeout" in error_str:
                logger.warning(f"Click intercepted, retrying with force=True")
                try:
                    # Wait extra for any overlays
                    await asyncio.sleep(0.5)
                    await self._wait_for_loading_overlays()
                    await asyncio.sleep(0.3)
                    # Retry with force
                    return await _attempt_click(use_force=True)
                except Exception as retry_error:
                    raise BrowserError(f"Failed to click element {index} (force retry also failed): {retry_error}")
            raise BrowserError(f"Failed to click element {index}: {first_error}")
    
    async def click_coordinates(
        self,
        x: int,
        y: int,
        button: str = "left"
    ) -> None:
        """Click at specific coordinates."""
        await self.page.mouse.click(x, y, button=button)
        logger.debug(f"Clicked at ({x}, {y})")
    
    async def type_text(
        self,
        index: int,
        text: str,
        clear: bool = True,
        delay: int = 0
    ) -> None:
        """
        Type text into an element.
        
        Args:
            index: Element index from selector map
            text: Text to type
            clear: Clear existing content first
            delay: Delay between keystrokes in ms
        """
        element_info = self._selector_map.get(index)
        if not element_info:
            raise ElementNotFoundError(
                f"index={index}",
                "Element not found in selector map"
            )
        
        try:
            # Wait for loading overlays to disappear
            await self._wait_for_loading_overlays()
            
            # Try XPath first (most reliable)
            xpath = element_info.get("xpath")
            if xpath:
                locator = self.page.locator(f"xpath={xpath}")
                
                # Click to focus
                await locator.click()
                await asyncio.sleep(0.1)
                
                # Clear if requested
                if clear:
                    try:
                        # Try fill() first (works for input/textarea)
                        await locator.fill("")
                    except Exception:
                        # For contenteditable elements, use keyboard shortcuts
                        await self.page.keyboard.press("Meta+a")  # Select all (Mac)
                        await self.page.keyboard.press("Backspace")
                        await asyncio.sleep(0.05)
                
                # Type the text
                await locator.type(text, delay=delay)
                logger.debug(f"Typed {len(text)} chars into element {index} via xpath")
                return
            
            # Fallback: Click at coordinates then type
            x = element_info.get("center_x")
            y = element_info.get("center_y")
            
            if x is not None and y is not None:
                await self.page.mouse.click(x, y)
                
                if clear:
                    await self.page.keyboard.press("Control+a")
                    await self.page.keyboard.press("Backspace")
                
                await self.page.keyboard.type(text, delay=delay)
                logger.debug(f"Typed {len(text)} chars into element {index} at ({x}, {y})")
                return
            
            raise BrowserError(f"Could not find element {index}")
            
        except Exception as e:
            raise BrowserError(f"Failed to type into element {index}: {e}")
    
    async def scroll(
        self,
        direction: str = "down",
        amount: int = 0,
        element_index: Optional[int] = None
    ) -> None:
        """
        Scroll the page or an element.
        
        Args:
            direction: up, down, left, right
            amount: Pixels to scroll (0 = viewport height)
            element_index: Element to scroll (None = page)
        """
        if amount == 0:
            # Default to viewport height
            viewport = await self.get_viewport_size()
            amount = viewport["height"]
        
        delta_x = 0
        delta_y = 0
        
        if direction == "down":
            delta_y = amount
        elif direction == "up":
            delta_y = -amount
        elif direction == "right":
            delta_x = amount
        elif direction == "left":
            delta_x = -amount
        
        if element_index is not None:
            # Scroll element
            element_info = self._selector_map.get(element_index)
            if element_info:
                script = f"""
                    const el = document.evaluate(
                        '{element_info.get("xpath", "//")}',
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    ).singleNodeValue;
                    if (el) el.scrollBy({delta_x}, {delta_y});
                """
                await self.page.evaluate(script)
        else:
            # Scroll page
            await self.page.mouse.wheel(delta_x, delta_y)
        
        logger.debug(f"Scrolled {direction} by {amount}px")
    
    async def send_keys(self, keys: str) -> None:
        """
        Send keyboard keys.
        
        Args:
            keys: Space-separated keys (e.g., "Enter", "Tab Tab ArrowDown")
        """
        key_list = keys.split()
        for key in key_list:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.05)
        
        logger.debug(f"Sent keys: {keys}")
    
    async def get_viewport_size(self) -> Dict[str, int]:
        """Get the viewport dimensions."""
        viewport = self.page.viewport_size
        return {
            "width": viewport["width"] if viewport else self.config.viewport_width,
            "height": viewport["height"] if viewport else self.config.viewport_height
        }
    
    async def get_scroll_position(self) -> Dict[str, float]:
        """Get the current scroll position."""
        result = await self.page.evaluate("""
            () => ({
                x: window.scrollX || window.pageXOffset,
                y: window.scrollY || window.pageYOffset,
                maxX: document.documentElement.scrollWidth - window.innerWidth,
                maxY: document.documentElement.scrollHeight - window.innerHeight,
                pageWidth: document.documentElement.scrollWidth,
                pageHeight: document.documentElement.scrollHeight
            })
        """)
        return result
    
    async def get_tabs(self) -> List[TabInfo]:
        """Get information about all open tabs."""
        tabs = []
        for i, page in enumerate(self._context.pages):
            try:
                title = await page.title()
            except Exception:
                title = ""
            tabs.append(TabInfo(
                target_id=str(i),
                url=page.url,
                title=title,
                is_active=(page == self._page)
            ))
        return tabs
    
    async def switch_tab(self, index: int) -> None:
        """Switch to a different tab by index."""
        pages = self._context.pages
        if 0 <= index < len(pages):
            self._page = pages[index]
            await self._page.bring_to_front()
            self._cdp_session = await self._page.context.new_cdp_session(self._page)
            logger.debug(f"Switched to tab {index}")
        else:
            raise BrowserError(f"Invalid tab index: {index}")
    
    async def new_tab(self, url: Optional[str] = None) -> None:
        """Open a new tab."""
        new_page = await self._context.new_page()
        self._page = new_page
        self._cdp_session = await self._page.context.new_cdp_session(self._page)
        
        if url:
            await self.navigate(url)
        
        logger.debug(f"Opened new tab{': ' + url if url else ''}")
    
    async def close_tab(self, index: Optional[int] = None) -> None:
        """Close a tab by index (current tab if None)."""
        pages = self._context.pages
        
        if index is None:
            page_to_close = self._page
        elif 0 <= index < len(pages):
            page_to_close = pages[index]
        else:
            raise BrowserError(f"Invalid tab index: {index}")
        
        await page_to_close.close()
        
        # Switch to another tab if needed
        if page_to_close == self._page and len(self._context.pages) > 0:
            self._page = self._context.pages[-1]
            self._cdp_session = await self._page.context.new_cdp_session(self._page)
        
        logger.debug(f"Closed tab {index if index is not None else 'current'}")
    
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in the page."""
        try:
            result = await self.page.evaluate(script)
            return result
        except Exception as e:
            raise BrowserError(f"Script execution failed: {e}")
    
    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None
    ) -> None:
        """Wait for a selector to appear."""
        timeout = timeout or self.config.timeout
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            raise TimeoutError("wait_for_selector", timeout)
    
    async def wait_for_load_state(
        self,
        state: str = "domcontentloaded"
    ) -> None:
        """Wait for a specific load state."""
        await self.page.wait_for_load_state(state)
    
    async def get_dom_snapshot(self) -> Dict[str, Any]:
        """
        Get a comprehensive DOM snapshot using CDP.
        
        Returns a snapshot containing:
        - Document structure
        - Computed styles
        - Layout information
        """
        if not self._cdp_session:
            raise BrowserError("CDP session not available")
        
        # Get DOM snapshot with layout info
        snapshot = await self._cdp_session.send(
            "DOMSnapshot.captureSnapshot",
            {
                "computedStyles": [
                    "display", "visibility", "opacity",
                    "position", "overflow", "pointer-events"
                ],
                "includePaintOrder": True,
                "includeDOMRects": True
            }
        )
        
        return snapshot
    
    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """Get the accessibility tree using CDP."""
        if not self._cdp_session:
            raise BrowserError("CDP session not available")
        
        tree = await self._cdp_session.send("Accessibility.getFullAXTree")
        return tree
    
    async def get_interactive_elements(self) -> Tuple[List[InteractiveElement], Dict[int, Dict]]:
        """
        Extract all interactive elements from the page.
        
        Returns:
            Tuple of (elements list, selector map)
        """
        # JavaScript to extract interactive elements
        script = """
        () => {
            const isVisible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return (
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    rect.width > 0 &&
                    rect.height > 0
                );
            };
            
            const isInteractive = (el) => {
                const tag = el.tagName.toLowerCase();
                const role = el.getAttribute('role');
                const clickable = ['a', 'button', 'input', 'select', 'textarea', 'label'];
                const interactiveRoles = ['button', 'link', 'menuitem', 'option', 'tab', 'checkbox', 'radio'];
                
                return (
                    clickable.includes(tag) ||
                    interactiveRoles.includes(role) ||
                    el.hasAttribute('onclick') ||
                    el.hasAttribute('tabindex') ||
                    el.getAttribute('contenteditable') === 'true'
                );
            };
            
            const elements = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_ELEMENT,
                null,
                false
            );
            
            let index = 1;
            let node;
            while (node = walker.nextNode()) {
                if (isVisible(node) && isInteractive(node)) {
                    const rect = node.getBoundingClientRect();
                    const attrs = {};
                    for (const attr of node.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    
                    elements.push({
                        index: index,
                        tagName: node.tagName.toLowerCase(),
                        text: node.innerText?.slice(0, 200) || '',
                        attributes: attrs,
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        role: node.getAttribute('role'),
                        ariaLabel: node.getAttribute('aria-label'),
                        isEditable: ['input', 'textarea'].includes(node.tagName.toLowerCase()) ||
                                   node.getAttribute('contenteditable') === 'true',
                        xpath: getXPath(node)
                    });
                    index++;
                }
            }
            
            function getXPath(el) {
                if (el.id) return '//*[@id="' + el.id + '"]';
                if (el === document.body) return '/html/body';
                
                let ix = 0;
                const siblings = el.parentNode?.childNodes || [];
                for (let i = 0; i < siblings.length; i++) {
                    const sibling = siblings[i];
                    if (sibling === el) {
                        return getXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    }
                    if (sibling.nodeType === 1 && sibling.tagName === el.tagName) {
                        ix++;
                    }
                }
                return '';
            }
            
            return elements;
        }
        """
        
        raw_elements = await self.page.evaluate(script)
        
        elements = []
        self._selector_map = {}
        
        for raw in raw_elements:
            element = InteractiveElement(
                index=raw["index"],
                tag_name=raw["tagName"],
                text=raw["text"],
                attributes=raw["attributes"],
                x=raw["x"],
                y=raw["y"],
                width=raw["width"],
                height=raw["height"],
                role=raw.get("role"),
                aria_label=raw.get("ariaLabel"),
                is_editable=raw.get("isEditable", False),
                is_visible=True,
                is_enabled=True,
                is_clickable=True,
            )
            elements.append(element)
            
            self._selector_map[raw["index"]] = {
                "xpath": raw.get("xpath"),
                "attributes": raw["attributes"],
                "tag_name": raw["tagName"],
                "center_x": raw["x"] + raw["width"] / 2,
                "center_y": raw["y"] + raw["height"] / 2,
            }
        
        return elements, self._selector_map
    
    async def get_browser_state(self) -> BrowserState:
        """Get the complete current browser state."""
        # Get basic page info
        url = await self.get_url()
        title = await self.get_title()
        
        # Get viewport and scroll info
        viewport = await self.get_viewport_size()
        scroll = await self.get_scroll_position()
        
        # Get tabs
        tabs = await self.get_tabs()
        
        # Get interactive elements
        elements, _ = await self.get_interactive_elements()
        
        # Take screenshot
        screenshot = await self.screenshot()
        
        return BrowserState(
            url=url,
            title=title,
            viewport_width=viewport["width"],
            viewport_height=viewport["height"],
            scroll_x=scroll["x"],
            scroll_y=scroll["y"],
            page_width=scroll["pageWidth"],
            page_height=scroll["pageHeight"],
            tabs=tabs,
            active_tab_id=str(self._context.pages.index(self._page)) if self._page else None,
            elements=elements,
            screenshot_b64=screenshot,
        )
    
    async def highlight_element(
        self,
        index: int,
        color: str = "rgba(255, 0, 0, 0.3)",
        duration_ms: int = 1000
    ) -> None:
        """Highlight an element temporarily for debugging."""
        element_info = self._selector_map.get(index)
        if not element_info:
            return
        
        xpath = element_info.get("xpath")
        if xpath:
            script = f"""
                const el = document.evaluate(
                    '{xpath}',
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                ).singleNodeValue;
                if (el) {{
                    const originalBg = el.style.backgroundColor;
                    el.style.backgroundColor = '{color}';
                    setTimeout(() => {{
                        el.style.backgroundColor = originalBg;
                    }}, {duration_ms});
                }}
            """
            await self.page.evaluate(script)

