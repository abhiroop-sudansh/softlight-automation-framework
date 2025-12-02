"""Tutorial Agent - Captures UI workflows while performing tasks."""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urlparse

from pydantic import BaseModel

from softlight_automation_framework.core.exceptions import (
    MaxStepsReachedError,
    MaxFailuresReachedError,
    LLMResponseError,
)
from softlight_automation_framework.browser.session import BrowserSession
from softlight_automation_framework.tools.registry import ToolRegistry
from softlight_automation_framework.tools.actions import create_default_registry
from softlight_automation_framework.tools.views import ActionResult
from softlight_automation_framework.llm.openai_client import OpenAIClient
from softlight_automation_framework.llm.schema import AgentOutput
from softlight_automation_framework.agent.prompts import SystemPrompt
from softlight_automation_framework.agent.message_manager import create_message_manager
from softlight_automation_framework.agent.views import (
    AgentState,
    AgentSettings,
    AgentHistory,
    AgentHistoryList,
    AgentStepInfo,
    StepMetadata,
)
from softlight_automation_framework.tutorial.capture import WorkflowCapture
from softlight_automation_framework.tutorial.views import TaskRequest, TutorialWorkflow

logger = logging.getLogger(__name__)


# Enhanced system prompt for tutorial generation
TUTORIAL_SYSTEM_PROMPT = """You are an expert AI assistant that demonstrates how to use web applications.

Your role is to:
1. Navigate web applications to complete the user's requested task
2. Perform each action step-by-step so it can be captured as a tutorial
3. Explain what you're doing at each step

<planning_first>
Before taking action, PLAN your approach:
1. What is the end goal?
2. What's the most direct path to get there?
3. For settings tasks: Can I navigate directly to a settings URL?
4. Are there keyboard shortcuts available? (Many apps use Cmd+, or Ctrl+, for settings)
</planning_first>

<smart_navigation>
USE DIRECT URLS when possible:
- Notion settings: https://www.notion.so/profile (for account) or look for Settings & members in sidebar
- Linear settings: https://linear.app/settings
- GitHub settings: https://github.com/settings
- For sub-pages, try appending /settings/[section] to the base URL
</smart_navigation>

<handling_overlays_and_popups>
CRITICAL: If you see a modal, popup, overlay, or dialog blocking what you need to click:
1. FIRST: Press Escape key using send_keys: {{"keys": "Escape"}}
2. If that doesn't work, look for X button, "Close", "Cancel", "Skip", or "Not now" buttons
3. Click OUTSIDE the modal on a dark/overlay area
4. NEVER click the same element more than 2 times
5. If a "Download app" or "Upgrade" popup appears, dismiss it immediately
</handling_overlays_and_popups>

<keyboard_shortcuts>
TRY KEYBOARD NAVIGATION when clicking fails:
- Tab / Shift+Tab to move between elements
- Enter to activate buttons/links  
- Escape to close modals
- Arrow keys to navigate menus
- Cmd+, or Ctrl+, often opens settings in desktop apps
</keyboard_shortcuts>

<finding_settings>
For SETTINGS tasks, look for:
1. Gear icon (⚙️) - usually in sidebar, header, or profile menu
2. Profile picture/avatar - clicking often shows settings menu
3. "Settings", "Preferences", "Options" in menus
4. Three dots menu (...) or hamburger menu (≡)
5. Direct navigation to /settings URL
</finding_settings>

<avoiding_loops>
NEVER repeat the same action more than twice!
- If you clicked something and nothing changed, DON'T click it again
- Try a DIFFERENT approach: keyboard navigation, direct URL, different element
- If truly stuck, use 'done' action with success=false and explain the blocker
</avoiding_loops>

<completing_toggle_tasks>
For TOGGLE tasks:
1. Navigate to the correct settings section
2. Find the toggle by its label text
3. Click directly on the toggle switch (not just the label)
4. Verify the toggle state changed
5. Complete with success=true and confirm the change
</completing_toggle_tasks>

{task_context}

{output_format}
"""


class TutorialAgent:
    """
    Agent that captures UI workflows while performing tasks.
    
    Extends base Agent functionality with:
    - Screenshot capture at each step
    - Workflow documentation generation
    - Tutorial export (markdown, JSON)
    
    Usage:
        agent = TutorialAgent(
            query="How do I create a project in Linear?",
            start_url="https://linear.app"
        )
        workflow = await agent.run()
        # Screenshots saved to datasets/how_do_i_create_a_project_in_linear/
    """
    
    def __init__(
        self,
        query: str,
        llm: Optional[OpenAIClient] = None,
        browser: Optional[BrowserSession] = None,
        start_url: Optional[str] = None,
        app_hint: Optional[str] = None,
        max_steps: int = 20,
        max_failures: int = 3,
        datasets_dir: str = "./datasets",
        headless: bool = False,
        session_file: Optional[str] = None,
    ):
        """
        Initialize the tutorial agent.
        
        Args:
            query: Natural language task query (e.g., "How do I create a project in Linear?")
            llm: LLM client (creates default if not provided)
            browser: Browser session (creates new if not provided)
            start_url: Starting URL (inferred from query if not provided)
            app_hint: Hint about which app to use
            max_steps: Maximum steps to attempt
            max_failures: Maximum consecutive failures
            datasets_dir: Directory to save captured workflows
            headless: Run browser in headless mode
        """
        self.query = query
        self.start_url = start_url
        self.app_hint = app_hint
        self.max_steps = max_steps
        self.max_failures = max_failures
        self.datasets_dir = datasets_dir
        self.headless = headless
        self.session_file = session_file
        
        # LLM and browser (may be created later)
        self._llm = llm
        self._browser = browser
        self._owns_browser = browser is None
        
        # Tools
        self.tools = create_default_registry()
        self._action_model = self.tools.get_action_model()
        
        # State
        self.state = AgentState()
        self.history = AgentHistoryList()
        
        # Loop detection - track recent actions
        self._recent_actions: List[str] = []
        self._max_repeated_actions = 2  # Stop after 2 repeated clicks on same element
        
        # Task request and capture
        self.task_request = TaskRequest(
            query=query,
            app_hint=app_hint,
            start_url=start_url,
            max_steps=max_steps,
        )
        self.capture = WorkflowCapture(
            base_dir=datasets_dir,
            task_request=self.task_request,
        )
        
        # Infer app info
        self._app_name, self._app_url = self._infer_app_info()
        
        # Create system prompt
        self._create_prompts()
    
    def _infer_app_info(self) -> tuple:
        """Infer application name and URL from query."""
        query_lower = self.query.lower()
        
        # Known app mappings
        app_mappings = {
            "linear": ("Linear", "https://linear.app"),
            "notion": ("Notion", "https://notion.so"),
            "github": ("GitHub", "https://github.com"),
            "gitlab": ("GitLab", "https://gitlab.com"),
            "jira": ("Jira", "https://atlassian.net"),
            "trello": ("Trello", "https://trello.com"),
            "asana": ("Asana", "https://asana.com"),
            "slack": ("Slack", "https://slack.com"),
            "figma": ("Figma", "https://figma.com"),
            "google docs": ("Google Docs", "https://docs.google.com"),
            "google sheets": ("Google Sheets", "https://sheets.google.com"),
            "google drive": ("Google Drive", "https://drive.google.com"),
            "dropbox": ("Dropbox", "https://dropbox.com"),
            "airtable": ("Airtable", "https://airtable.com"),
            "monday": ("Monday.com", "https://monday.com"),
            "clickup": ("ClickUp", "https://clickup.com"),
            "todoist": ("Todoist", "https://todoist.com"),
            "spotify": ("Spotify", "https://open.spotify.com"),
            "youtube": ("YouTube", "https://youtube.com"),
            "twitter": ("Twitter/X", "https://twitter.com"),
            "linkedin": ("LinkedIn", "https://linkedin.com"),
            "reddit": ("Reddit", "https://reddit.com"),
            "amazon": ("Amazon", "https://amazon.com"),
            "ebay": ("eBay", "https://ebay.com"),
        }
        
        # Check for app mentions in query
        for key, (name, url) in app_mappings.items():
            if key in query_lower:
                return (name, self.start_url or url)
        
        # Use app hint if provided
        if self.app_hint:
            hint_lower = self.app_hint.lower()
            for key, (name, url) in app_mappings.items():
                if key in hint_lower:
                    return (name, self.start_url or url)
        
        # Use start URL if provided
        if self.start_url:
            parsed = urlparse(self.start_url)
            domain = parsed.netloc.replace("www.", "")
            name = domain.split(".")[0].title()
            return (name, self.start_url)
        
        # Default to generic
        return ("Web Application", self.start_url or "about:blank")
    
    def _create_prompts(self) -> None:
        """Create system prompts for tutorial generation."""
        task_context = f"""<task>
Original request: {self.query}
Application: {self._app_name}
Starting URL: {self._app_url}
</task>"""

        output_format = """<output_format>
You MUST respond with valid JSON only. Use this exact format:
{
  "thinking": "What I observe and my plan",
  "evaluation_previous_goal": "Assessment of last action",
  "memory": "Key information to remember",
  "next_goal": "What I'm about to do and why",
  "action": [
    {"navigate": {"url": "https://example.com"}},
    {"click": {"index": 5}},
    {"input": {"index": 3, "text": "hello"}},
    {"done": {"text": "Task completed", "success": true}}
  ]
}

Available actions:
- navigate: {"url": "...", "new_tab": false}
- click: {"index": N} or {"coordinate_x": X, "coordinate_y": Y}  
- input: {"index": N, "text": "...", "clear": true}
- scroll: {"down": true, "pages": 1.0}
- wait: {"seconds": 3}
- send_keys: {"keys": "Enter"}
- go_back: {}
- extract: {"query": "what to extract"}
- screenshot: {}
- done: {"text": "summary of what was done", "success": true}

IMPORTANT: Take ONE action at a time for clear tutorial steps!
</output_format>"""

        self._system_message = TUTORIAL_SYSTEM_PROMPT.format(
            task_context=task_context,
            output_format=output_format,
        )
    
    @property
    def llm(self) -> OpenAIClient:
        """Get or create LLM client."""
        if self._llm is None:
            self._llm = OpenAIClient(model="gpt-4o")
        return self._llm
    
    async def _ensure_browser(self) -> BrowserSession:
        """Ensure browser session exists."""
        if self._browser is None:
            self._browser = BrowserSession(
                headless=self.headless,
                session_file=self.session_file,
            )
            await self._browser.start()
            self._owns_browser = True
        return self._browser
    
    async def run(self) -> TutorialWorkflow:
        """
        Run the tutorial agent and capture the workflow.
        
        Returns:
            TutorialWorkflow with captured steps and screenshots
        """
        logger.info(f"🎬 Starting tutorial capture: {self.query}")
        
        browser = await self._ensure_browser()
        
        # Start workflow capture (ensure app_url is never None)
        self.capture.start_workflow(
            app_name=self._app_name,
            app_url=self._app_url if self._app_url else "about:blank",
        )
        
        # Create message manager with custom system prompt
        from softlight_automation_framework.agent.prompts import SystemPrompt
        
        custom_prompt = SystemPrompt(
            override_system_message=self._system_message,
        )
        self._message_manager = create_message_manager(
            task=self.query,
            system_prompt=custom_prompt,
            compact=True,
        )
        
        self.state.start_time = datetime.now()
        self.state.n_steps = 0
        
        try:
            # Navigate to starting URL
            if self._app_url and self._app_url != "about:blank":
                await browser.navigate(self._app_url)
                
                # Wait for page to stabilize
                await asyncio.sleep(1)
                
                # Try to dismiss any initial popups by pressing Escape
                try:
                    await browser.send_keys("Escape")
                    await asyncio.sleep(0.3)
                except:
                    pass
                
                # Capture initial state
                state = await browser.get_state(force_refresh=True)
                self.capture.capture_state(
                    url=state.url,
                    title=state.title,
                    screenshot_b64=state.screenshot_b64 or "",
                    action_taken=f"Navigate to {self._app_name}",
                    action_type="navigate",
                    annotation=f"Starting point: {self._app_name}",
                )
            
            # Main execution loop
            while not self.state.is_done and self.state.n_steps < self.max_steps:
                if self.state.is_stopped:
                    break
                
                try:
                    await self._execute_step(browser)
                except Exception as e:
                    logger.error(f"Step {self.state.n_steps} failed: {e}")
                    self.state.consecutive_failures += 1
                    
                    if self.state.consecutive_failures >= self.max_failures:
                        raise MaxFailuresReachedError(self.max_failures)
                
                self.state.n_steps += 1
            
            # Complete workflow
            success = self.state.success or False
            summary = self._generate_summary()
            
            workflow = self.capture.complete_workflow(
                success=success,
                summary=summary,
            )
            
            return workflow
            
        finally:
            self.state.end_time = datetime.now()
            
            # Close browser if we created it
            if self._owns_browser and self._browser:
                await self._browser.stop()
                self._browser = None
            
            duration = (self.state.end_time - self.state.start_time).total_seconds()
            logger.info(f"🎬 Tutorial capture complete: {self.state.n_steps} steps, {duration:.1f}s")
    
    async def _execute_step(self, browser: BrowserSession) -> None:
        """Execute a single agent step with capture."""
        step_start = time.time()
        step_number = self.state.n_steps
        
        # Get current browser state
        browser_state = await browser.get_state(force_refresh=True)
        
        # Build step info
        step_info = AgentStepInfo(
            step_number=step_number,
            max_steps=self.max_steps,
        )
        
        # Build messages for LLM
        messages = self._message_manager.build_step_message(
            browser_state=browser_state,
            agent_history=self.history,
            step_info=step_info.to_dict(),
            include_screenshot=True,
        )
        
        # Get LLM response
        response = await self.llm.complete(
            messages=messages,
            response_format=AgentOutput,
        )
        
        self._message_manager.add_assistant_response(response.content)
        
        # Parse output
        agent_output = self._parse_response(response.content)
        
        # Execute actions and capture each one
        results = await self._execute_and_capture_actions(
            browser,
            agent_output,
        )
        
        # Create history entry
        step_end = time.time()
        history_entry = AgentHistory(
            model_output=agent_output,
            results=results,
            url=browser_state.url,
            title=browser_state.title,
            screenshot_b64=browser_state.screenshot_b64,
            metadata=StepMetadata(
                step_number=step_number,
                start_time=step_start,
                end_time=step_end,
            ),
        )
        
        self.history.add(history_entry)
        self.state.last_output = agent_output
        self.state.last_result = results
        
        # Check if done
        for result in results:
            if result.is_done:
                self.state.is_done = True
                self.state.success = result.success
                break
        
        # Reset failure counter on success
        if not any(r.error for r in results):
            self.state.consecutive_failures = 0
    
    def _parse_response(self, content: str) -> AgentOutput:
        """Parse LLM response into AgentOutput."""
        try:
            data = json.loads(content)
            
            actions = data.get("action", [])
            if not actions:
                raise ValueError("No actions in response")
            
            validated_actions = []
            for action in actions:
                if isinstance(action, dict):
                    validated_actions.append(action)
            
            return AgentOutput(
                thinking=data.get("thinking"),
                evaluation_previous_goal=data.get("evaluation_previous_goal"),
                memory=data.get("memory"),
                next_goal=data.get("next_goal"),
                action=validated_actions,
            )
            
        except json.JSONDecodeError as e:
            raise LLMResponseError(f"Invalid JSON: {e}", raw_response=content)
        except Exception as e:
            raise LLMResponseError(f"Failed to parse response: {e}", raw_response=content)
    
    async def _execute_and_capture_actions(
        self,
        browser: BrowserSession,
        agent_output: AgentOutput,
    ) -> List[ActionResult]:
        """Execute actions and capture UI state after each."""
        results = []
        
        for action in agent_output.action[:4]:  # Max 4 actions per step
            if not action:
                continue
            
            action_name = list(action.keys())[0]
            params = action[action_name]
            
            # Create action signature for loop detection
            action_sig = f"{action_name}:{json.dumps(params, sort_keys=True)}"
            
            # Check for repeated actions (loop detection)
            if self._is_action_repeated(action_sig):
                logger.warning(f"🔄 Loop detected: {action_name} repeated too many times")
                # Try to break the loop by pressing Escape
                try:
                    await browser.send_keys("Escape")
                    await asyncio.sleep(0.5)
                except:
                    pass
                
                # If still looping, force completion
                if self._count_repeated_actions(action_sig) >= self._max_repeated_actions + 2:
                    logger.warning("⚠️ Breaking out of action loop")
                    results.append(ActionResult(
                        is_done=True,
                        success=False,
                        extracted_content="Task incomplete - got stuck in a loop clicking the same element. There may be a popup or overlay blocking the target.",
                    ))
                    break
            
            # Track this action
            self._recent_actions.append(action_sig)
            if len(self._recent_actions) > 10:
                self._recent_actions.pop(0)
            
            logger.debug(f"Executing action: {action_name}")
            
            try:
                # Execute action
                result = await self.tools.execute(
                    action_name=action_name,
                    params=params,
                    browser_session=browser,
                    llm=self.llm,
                )
                
                results.append(result)
                
                # Capture UI state after action
                await self._capture_action_state(
                    browser=browser,
                    action_name=action_name,
                    params=params,
                    result=result,
                    agent_thinking=agent_output.thinking,
                    next_goal=agent_output.next_goal,
                )
                
                # Stop on error or done
                if result.error or result.is_done:
                    break
                
            except Exception as e:
                error_str = str(e).lower()
                # Don't break on navigation-related errors (context destroyed)
                if "execution context" in error_str or "navigation" in error_str:
                    logger.warning(f"Navigation-related error (recoverable): {e}")
                    await asyncio.sleep(0.5)  # Wait for navigation to complete
                    results.append(ActionResult(error=None))  # Continue
                else:
                    logger.error(f"Action failed: {e}")
                    results.append(ActionResult(error=str(e)))
                    break
        
        return results if results else [ActionResult()]
    
    def _is_action_repeated(self, action_sig: str) -> bool:
        """Check if an action has been repeated too many times."""
        count = self._count_repeated_actions(action_sig)
        return count >= self._max_repeated_actions
    
    def _count_repeated_actions(self, action_sig: str) -> int:
        """Count how many times an action appears in recent history."""
        return sum(1 for a in self._recent_actions if a == action_sig)
    
    async def _capture_action_state(
        self,
        browser: BrowserSession,
        action_name: str,
        params: Dict[str, Any],
        result: ActionResult,
        agent_thinking: Optional[str] = None,
        next_goal: Optional[str] = None,
    ) -> None:
        """Capture UI state after an action."""
        # Skip capture for certain actions
        if action_name in ["wait", "screenshot"]:
            return
        
        # Get fresh browser state
        state = await browser.get_state(force_refresh=True)
        
        # Generate action description
        action_description = self._describe_action(action_name, params, result)
        
        # Get element description if applicable
        element_description = None
        element_index = None
        
        if action_name in ["click", "input", "type"]:
            element_index = params.get("index")
            if element_index is not None:
                # Try to get element info
                element = await browser.get_element_by_index(element_index)
                if element:
                    element_description = element.get_description()
        
        # Capture the state
        self.capture.capture_state(
            url=state.url,
            title=state.title,
            screenshot_b64=state.screenshot_b64 or "",
            action_taken=action_description,
            action_type=action_name,
            element_description=element_description,
            element_index=element_index,
            agent_thinking=agent_thinking,
            next_goal=next_goal,
        )
    
    def _describe_action(
        self,
        action_name: str,
        params: Dict[str, Any],
        result: ActionResult,
    ) -> str:
        """Generate human-readable action description."""
        if action_name == "navigate":
            return f"Navigated to {params.get('url', 'page')}"
        elif action_name == "click":
            idx = params.get("index")
            if idx is not None:
                return f"Clicked on element {idx}"
            return f"Clicked at position ({params.get('coordinate_x')}, {params.get('coordinate_y')})"
        elif action_name in ["input", "type"]:
            text = params.get("text", "")
            preview = text[:30] + "..." if len(text) > 30 else text
            return f"Typed '{preview}'"
        elif action_name == "scroll":
            direction = "down" if params.get("down", True) else "up"
            return f"Scrolled {direction}"
        elif action_name == "go_back":
            return "Navigated back"
        elif action_name == "send_keys":
            return f"Pressed {params.get('keys', 'key')}"
        elif action_name == "extract":
            return f"Extracted content for: {params.get('query', 'query')}"
        elif action_name == "done":
            return "Task completed"
        else:
            return f"Performed {action_name}"
    
    def _generate_summary(self) -> str:
        """Generate workflow summary."""
        if self.state.success:
            return f"Successfully demonstrated: {self.query}"
        else:
            return f"Attempted to demonstrate: {self.query} (incomplete)"


async def run_tutorial(
    query: str,
    start_url: Optional[str] = None,
    app_hint: Optional[str] = None,
    model: str = "gpt-4o",
    headless: bool = False,
    max_steps: int = 20,
    datasets_dir: str = "./datasets",
) -> TutorialWorkflow:
    """
    Convenience function to run a tutorial capture.
    
    Args:
        query: Task query (e.g., "How do I create a project in Linear?")
        start_url: Starting URL (optional, inferred from query)
        app_hint: Hint about which app
        model: LLM model to use
        headless: Run browser in headless mode
        max_steps: Maximum steps
        datasets_dir: Directory to save captured workflows
        
    Returns:
        TutorialWorkflow with captured steps
    """
    llm = OpenAIClient(model=model)
    
    agent = TutorialAgent(
        query=query,
        llm=llm,
        start_url=start_url,
        app_hint=app_hint,
        max_steps=max_steps,
        headless=headless,
        datasets_dir=datasets_dir,
    )
    
    return await agent.run()

