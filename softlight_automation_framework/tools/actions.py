"""Default browser actions implementation."""

import asyncio
import logging
import urllib.parse
from typing import Any, Optional

from softlight_automation_framework.tools.registry import ToolRegistry
from softlight_automation_framework.tools.views import (
    ActionResult,
    NavigateActionParams,
    SearchActionParams,
    ClickActionParams,
    InputActionParams,
    ScrollActionParams,
    WaitActionParams,
    ExtractActionParams,
    DoneActionParams,
    SendKeysActionParams,
    SwitchTabActionParams,
    CloseTabActionParams,
    NoParamsAction,
    DropdownOptionsActionParams,
    SelectDropdownActionParams,
    EvaluateActionParams,
)

logger = logging.getLogger(__name__)


# Re-export param models for convenience
NavigateAction = NavigateActionParams
ClickAction = ClickActionParams
InputAction = InputActionParams
ScrollAction = ScrollActionParams
WaitAction = WaitActionParams
ExtractAction = ExtractActionParams
DoneAction = DoneActionParams
SendKeysAction = SendKeysActionParams
GoBackAction = NoParamsAction
SwitchTabAction = SwitchTabActionParams
CloseTabAction = CloseTabActionParams
ScreenshotAction = NoParamsAction


def register_default_actions(registry: ToolRegistry) -> None:
    """
    Register all default browser actions with the registry.
    
    Args:
        registry: ToolRegistry to register actions with
    """
    
    @registry.action(
        description="Search the web using a search engine",
        param_model=SearchActionParams,
    )
    async def search(params: SearchActionParams, browser_session: Any) -> ActionResult:
        """Perform a web search."""
        encoded_query = urllib.parse.quote_plus(params.query)
        
        search_urls = {
            "google": f"https://www.google.com/search?q={encoded_query}",
            "bing": f"https://www.bing.com/search?q={encoded_query}",
            "duckduckgo": f"https://duckduckgo.com/?q={encoded_query}",
        }
        
        engine = params.engine.lower()
        if engine not in search_urls:
            return ActionResult(error=f"Unknown search engine: {engine}")
        
        url = search_urls[engine]
        await browser_session.navigate(url)
        
        memory = f"Searched {engine.title()} for '{params.query}'"
        logger.info(f"🔍 {memory}")
        
        return ActionResult(
            extracted_content=memory,
            long_term_memory=memory,
        )
    
    @registry.action(
        description="Navigate to a URL. Set new_tab=true to open in a new tab.",
        param_model=NavigateActionParams,
    )
    async def navigate(params: NavigateActionParams, browser_session: Any) -> ActionResult:
        """Navigate to a URL."""
        try:
            # Ensure URL has protocol
            url = params.url
            if not url.startswith(('http://', 'https://', 'file://')):
                url = 'https://' + url
            
            await browser_session.navigate(url, new_tab=params.new_tab)
            
            if params.new_tab:
                memory = f"Opened new tab with URL {url}"
            else:
                memory = f"Navigated to {url}"
            
            logger.info(f"🔗 {memory}")
            return ActionResult(
                extracted_content=memory,
                long_term_memory=memory,
            )
        except Exception as e:
            return ActionResult(error=f"Navigation failed: {str(e)}")
    
    @registry.action(
        description="Go back to the previous page in browser history",
        param_model=NoParamsAction,
    )
    async def go_back(params: NoParamsAction, browser_session: Any) -> ActionResult:
        """Go back in history."""
        await browser_session.go_back()
        memory = "Navigated back"
        logger.info(f"🔙 {memory}")
        return ActionResult(extracted_content=memory)
    
    @registry.action(
        description="Click on an element by index or coordinates. Prefer index when available.",
        param_model=ClickActionParams,
    )
    async def click(params: ClickActionParams, browser_session: Any) -> ActionResult:
        """Click on an element."""
        try:
            if params.index is not None:
                result = await browser_session.click(index=params.index)
                memory = f"Clicked element {params.index}"
            else:
                result = await browser_session.click(
                    x=params.coordinate_x,
                    y=params.coordinate_y
                )
                memory = f"Clicked at ({params.coordinate_x}, {params.coordinate_y})"
            
            logger.info(f"🖱️ {memory}")
            return ActionResult(
                extracted_content=memory,
                metadata=result,
            )
        except Exception as e:
            return ActionResult(error=f"Click failed: {str(e)}")
    
    @registry.action(
        description="Type text into an input element",
        param_model=InputActionParams,
    )
    async def input(params: InputActionParams, browser_session: Any) -> ActionResult:
        """Type text into an element."""
        try:
            await browser_session.type_text(
                index=params.index,
                text=params.text,
                clear=params.clear,
            )
            
            # Don't log sensitive data
            display_text = params.text if len(params.text) < 20 else f"{params.text[:17]}..."
            memory = f"Typed '{display_text}' into element {params.index}"
            
            logger.debug(f"⌨️ Typed into element {params.index}")
            return ActionResult(
                extracted_content=memory,
                long_term_memory=memory,
            )
        except Exception as e:
            return ActionResult(error=f"Input failed: {str(e)}")
    
    @registry.action(
        description="Scroll the page. down=True scrolls down, down=False scrolls up. pages controls scroll amount.",
        param_model=ScrollActionParams,
    )
    async def scroll(params: ScrollActionParams, browser_session: Any) -> ActionResult:
        """Scroll the page."""
        try:
            direction = "down" if params.down else "up"
            await browser_session.scroll(
                direction=direction,
                pages=params.pages,
                element_index=params.index,
            )
            
            target = f"element {params.index}" if params.index else "page"
            memory = f"Scrolled {direction} {params.pages} pages on {target}"
            
            logger.info(f"📜 {memory}")
            return ActionResult(
                extracted_content=memory,
                long_term_memory=memory,
            )
        except Exception as e:
            return ActionResult(error=f"Scroll failed: {str(e)}")
    
    @registry.action(
        description="Wait for a specified number of seconds (max 30)",
        param_model=WaitActionParams,
    )
    async def wait(params: WaitActionParams, browser_session: Any) -> ActionResult:
        """Wait for a specified time."""
        seconds = min(params.seconds, 30)  # Cap at 30 seconds
        await asyncio.sleep(seconds)
        
        memory = f"Waited for {seconds} seconds"
        logger.info(f"⏳ {memory}")
        
        return ActionResult(
            extracted_content=memory,
            long_term_memory=memory,
        )
    
    @registry.action(
        description="Extract information from the page based on a query",
        param_model=ExtractActionParams,
    )
    async def extract(
        params: ExtractActionParams,
        browser_session: Any,
        llm: Optional[Any] = None,
    ) -> ActionResult:
        """Extract content from the page."""
        try:
            # Get page content
            content = await browser_session.extract_content(params.query)
            
            if not content:
                return ActionResult(
                    extracted_content="No content found on page",
                    error="Page appears empty",
                )
            
            # Truncate if too long
            max_length = 5000
            if len(content) > max_length:
                content = content[:max_length] + "...[truncated]"
            
            url = browser_session.current_url
            result = f"<url>{url}</url>\n<query>{params.query}</query>\n<content>{content}</content>"
            
            memory = f"Extracted content for query: {params.query[:50]}"
            logger.info(f"📄 {memory}")
            
            return ActionResult(
                extracted_content=result,
                long_term_memory=memory,
            )
        except Exception as e:
            return ActionResult(error=f"Extraction failed: {str(e)}")
    
    @registry.action(
        description="Request a screenshot for the next observation",
        param_model=NoParamsAction,
    )
    async def screenshot(params: NoParamsAction, browser_session: Any) -> ActionResult:
        """Request a screenshot."""
        memory = "Requested screenshot for next observation"
        logger.info(f"📸 {memory}")
        
        return ActionResult(
            extracted_content=memory,
            include_screenshot=True,
        )
    
    @registry.action(
        description="Send keyboard keys (e.g., 'Enter', 'Tab Tab ArrowDown')",
        param_model=SendKeysActionParams,
    )
    async def send_keys(params: SendKeysActionParams, browser_session: Any) -> ActionResult:
        """Send keyboard keys."""
        await browser_session.send_keys(params.keys)
        
        memory = f"Sent keys: {params.keys}"
        logger.info(f"⌨️ {memory}")
        
        return ActionResult(
            extracted_content=memory,
            long_term_memory=memory,
        )
    
    @registry.action(
        description="Switch to a different browser tab by tab_id (last 4 chars of target_id)",
        param_model=SwitchTabActionParams,
    )
    async def switch(params: SwitchTabActionParams, browser_session: Any) -> ActionResult:
        """Switch to another tab."""
        try:
            await browser_session.switch_tab(params.tab_id)
            
            memory = f"Switched to tab {params.tab_id}"
            logger.info(f"🔄 {memory}")
            
            return ActionResult(
                extracted_content=memory,
                long_term_memory=memory,
            )
        except Exception as e:
            return ActionResult(error=f"Tab switch failed: {str(e)}")
    
    @registry.action(
        description="Close a browser tab by tab_id",
        param_model=CloseTabActionParams,
    )
    async def close(params: CloseTabActionParams, browser_session: Any) -> ActionResult:
        """Close a tab."""
        try:
            await browser_session.close_tab(params.tab_id)
            
            memory = f"Closed tab {params.tab_id}"
            logger.info(f"🗑️ {memory}")
            
            return ActionResult(
                extracted_content=memory,
                long_term_memory=memory,
            )
        except Exception as e:
            return ActionResult(error=f"Tab close failed: {str(e)}")
    
    @registry.action(
        description="Execute JavaScript code in the browser",
        param_model=EvaluateActionParams,
    )
    async def evaluate(params: EvaluateActionParams, browser_session: Any) -> ActionResult:
        """Execute JavaScript."""
        try:
            result = await browser_session.execute_script(params.code)
            
            # Format result
            if result is None:
                result_str = "undefined"
            elif isinstance(result, (dict, list)):
                import json
                result_str = json.dumps(result, indent=2)
            else:
                result_str = str(result)
            
            # Truncate if too long
            if len(result_str) > 2000:
                result_str = result_str[:2000] + "...[truncated]"
            
            logger.debug(f"JavaScript executed, result length: {len(result_str)}")
            
            return ActionResult(extracted_content=result_str)
        except Exception as e:
            return ActionResult(error=f"JavaScript execution failed: {str(e)}")
    
    @registry.action(
        description="Complete the task. Set success=true if task completed successfully.",
        param_model=DoneActionParams,
        is_terminal=True,
    )
    async def done(params: DoneActionParams, browser_session: Any = None) -> ActionResult:
        """Complete the task."""
        logger.info(f"✅ Task completed (success={params.success}): {params.text[:100]}")
        
        return ActionResult(
            is_done=True,
            success=params.success,
            extracted_content=params.text,
            long_term_memory=f"Task completed: {params.success}",
            attachments=params.files_to_display,
        )
    
    logger.debug(f"Registered {len(registry)} default actions")


def create_default_registry(
    exclude_actions: Optional[list] = None
) -> ToolRegistry:
    """
    Create a ToolRegistry with all default actions registered.
    
    Args:
        exclude_actions: List of action names to exclude
        
    Returns:
        Configured ToolRegistry
    """
    registry = ToolRegistry(exclude_actions=exclude_actions)
    register_default_actions(registry)
    return registry

