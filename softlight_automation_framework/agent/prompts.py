"""System prompts and message builders for the agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from softlight_automation_framework.llm.messages import (
    SystemMessage,
    UserMessage,
    ImageContent,
)

if TYPE_CHECKING:
    from softlight_automation_framework.browser.views import BrowserState


SYSTEM_PROMPT_TEMPLATE = """You are an AI agent designed to automate browser tasks. Your goal is to accomplish the task provided in <user_request>.

<capabilities>
You excel at:
1. Navigating complex websites and extracting information
2. Automating form submissions and interactive web actions
3. Following multi-step instructions precisely
4. Efficiently performing diverse web tasks
</capabilities>

<input>
At every step, you receive:
1. <agent_history>: Your previous actions and their results
2. <agent_state>: Current <user_request> and <step_info>
3. <browser_state>: Current URL, tabs, interactive elements, and page content
4. <screenshot>: Visual capture of the current page (if available)
</input>

<browser_state_format>
Interactive elements are shown as: [index]<tag attributes>text</tag>
- index: Numeric ID for interaction
- tag: HTML element type
- text: Visible content
- * prefix: New element since last step

Example:
[33]<div>User form</div>
    *[35]<button aria-label='Submit'>Submit</button>
</browser_state_format>

<rules>
1. Only interact with elements that have a numeric [index]
2. If expected elements are missing, try scrolling, waiting, or refreshing
3. Use scroll when content may be off-screen
4. If a captcha appears, try to solve it or find an alternative
5. When filling forms, verify input was accepted before proceeding
6. Use extract action for structured data extraction from page content
7. Call done action when task is complete or impossible to continue
</rules>

<action_rules>
- Maximum {max_actions} actions per step
- Actions execute sequentially
- Sequence stops if page changes
- Combine actions efficiently (e.g., input + click for form submission)
</action_rules>

<output_format>
You MUST respond with valid JSON only. No markdown, no extra text. Use this exact format:
{{
  "thinking": "Your reasoning about the current state and what to do next",
  "evaluation_previous_goal": "Assessment of your last action (success/failure/uncertain)",
  "memory": "Key information to remember (progress, data found, etc.)",
  "next_goal": "Your immediate next objective",
  "action": [
    {{"navigate": {{"url": "https://example.com"}}}},
    {{"click": {{"index": 5}}}},
    {{"input": {{"index": 3, "text": "hello"}}}},
    {{"done": {{"text": "Task completed", "success": true}}}}
  ]
}}

Available actions:
- navigate: {{"url": "...", "new_tab": false}}
- click: {{"index": N}} or {{"coordinate_x": X, "coordinate_y": Y}}
- input: {{"index": N, "text": "...", "clear": true}}
- scroll: {{"down": true, "pages": 1.0}}
- wait: {{"seconds": 3}}
- send_keys: {{"keys": "Enter"}}
- go_back: {{}}
- extract: {{"query": "what to extract"}}
- screenshot: {{}}
- done: {{"text": "result message", "success": true}}

Action list must contain at least one action. Use "done" to finish the task.
</output_format>

<completion_rules>
Call the done action when:
- Task is fully completed
- Task is impossible to continue
- Maximum steps reached

Set success=true only if the full task was completed.
Include all relevant findings in the done action's text field.
</completion_rules>"""


class SystemPrompt:
    """System prompt generator for the agent."""
    
    def __init__(
        self,
        max_actions_per_step: int = 4,
        override_system_message: Optional[str] = None,
        extend_system_message: Optional[str] = None,
        use_thinking: bool = True,
    ):
        """
        Initialize the system prompt.
        
        Args:
            max_actions_per_step: Maximum actions allowed per step
            override_system_message: Replace the entire system message
            extend_system_message: Append additional instructions
            use_thinking: Include thinking in output schema
        """
        self.max_actions_per_step = max_actions_per_step
        self.use_thinking = use_thinking
        
        # Build the prompt
        if override_system_message:
            prompt = override_system_message
        else:
            prompt = SYSTEM_PROMPT_TEMPLATE.format(
                max_actions=max_actions_per_step
            )
        
        if extend_system_message:
            prompt += f"\n\n{extend_system_message}"
        
        self._message = SystemMessage(content=prompt)
    
    def get_message(self) -> SystemMessage:
        """Get the system message."""
        return self._message


def build_user_message(
    browser_state: "BrowserState",
    task: str,
    agent_history: Optional[str] = None,
    step_info: Optional[Dict[str, Any]] = None,
    include_screenshot: bool = True,
) -> UserMessage:
    """
    Build a user message with browser state for the agent.
    
    Args:
        browser_state: Current browser state
        task: The user's task
        agent_history: Summary of previous actions
        step_info: Current step information
        include_screenshot: Whether to include screenshot
        
    Returns:
        UserMessage with all context
    """
    # Build state description
    parts = []
    
    # Agent history
    parts.append("<agent_history>")
    if agent_history:
        parts.append(agent_history)
    else:
        parts.append("No previous actions")
    parts.append("</agent_history>")
    
    # Agent state
    parts.append("\n<agent_state>")
    parts.append(f"<user_request>\n{task}\n</user_request>")
    
    if step_info:
        step_str = f"Step {step_info.get('step_number', 1)} of {step_info.get('max_steps', 100)}"
        parts.append(f"<step_info>{step_str}</step_info>")
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    parts.append(f"<date>{date_str}</date>")
    parts.append("</agent_state>")
    
    # Browser state
    parts.append("\n<browser_state>")
    parts.append(browser_state.to_llm_string())
    parts.append("</browser_state>")
    
    text_content = "\n".join(parts)
    
    # Include screenshot if available
    if include_screenshot and browser_state.screenshot_b64:
        return UserMessage.with_screenshot(
            text=text_content,
            screenshot_b64=browser_state.screenshot_b64,
            detail="auto"
        )
    else:
        return UserMessage(content=text_content)


def build_history_description(
    history: List[Dict[str, Any]],
    max_items: Optional[int] = None,
) -> str:
    """
    Build a description of agent history for context.
    
    Args:
        history: List of history items
        max_items: Maximum items to include (None = all)
        
    Returns:
        Formatted history string
    """
    if not history:
        return "No previous actions"
    
    items = history
    if max_items:
        items = history[-max_items:]
    
    lines = []
    for i, item in enumerate(items, 1):
        step_num = item.get("step_number", i)
        
        lines.append(f"<step_{step_num}>")
        
        # Add evaluation
        if item.get("evaluation"):
            lines.append(f"Evaluation: {item['evaluation']}")
        
        # Add memory
        if item.get("memory"):
            lines.append(f"Memory: {item['memory']}")
        
        # Add goal
        if item.get("next_goal"):
            lines.append(f"Goal: {item['next_goal']}")
        
        # Add action results
        actions = item.get("actions", [])
        if actions:
            for action in actions:
                action_name = action.get("name", "unknown")
                result = action.get("result", "")
                error = action.get("error")
                
                if error:
                    lines.append(f"Action: {action_name} -> Error: {error}")
                elif result:
                    lines.append(f"Action: {action_name} -> {result[:100]}")
                else:
                    lines.append(f"Action: {action_name}")
        
        lines.append(f"</step_{step_num}>")
    
    return "\n".join(lines)


# Extended prompts for specific scenarios

EXTRACTION_PROMPT = """You are an expert at extracting structured data from web pages.

Given the page content and a query, extract the relevant information accurately.

Rules:
- Only use information present in the page content
- Do not make up or guess information
- If information is not found, state that clearly
- Format output as requested by the query
"""

FORM_FILLING_PROMPT = """You are filling out a web form. Be precise and careful.

Rules:
- Verify each field is correctly filled before proceeding
- Use tab or click to move between fields
- Wait for auto-complete suggestions when relevant
- Submit only when all required fields are complete
"""

NAVIGATION_PROMPT = """You are navigating a website to find specific information.

Rules:
- Use search functionality when available
- Follow logical navigation paths
- Use breadcrumbs to track location
- Go back if you reach a dead end
"""


def get_scenario_prompt(scenario: str) -> str:
    """Get extended prompt for a specific scenario."""
    prompts = {
        "extraction": EXTRACTION_PROMPT,
        "form_filling": FORM_FILLING_PROMPT,
        "navigation": NAVIGATION_PROMPT,
    }
    return prompts.get(scenario, "")

