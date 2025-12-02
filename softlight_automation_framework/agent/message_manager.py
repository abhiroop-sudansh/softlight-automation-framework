"""Message history management for the agent."""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from softlight_automation_framework.llm.messages import (
    Message,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    MessageHistory,
    ImageContent,
)
from softlight_automation_framework.agent.prompts import (
    SystemPrompt,
    build_user_message,
    build_history_description,
)

if TYPE_CHECKING:
    from softlight_automation_framework.browser.views import BrowserState
    from softlight_automation_framework.agent.views import AgentHistoryList

logger = logging.getLogger(__name__)


class MessageManager:
    """
    Manages conversation history and message construction for the agent.
    
    Handles:
    - System prompt management
    - User message building with browser state
    - History truncation and summarization
    - Screenshot handling
    """
    
    def __init__(
        self,
        task: str,
        system_prompt: Optional[SystemPrompt] = None,
        max_history_messages: Optional[int] = None,
        max_history_items: Optional[int] = None,
    ):
        """
        Initialize the message manager.
        
        Args:
            task: The user's task
            system_prompt: Custom system prompt (or use default)
            max_history_messages: Max conversation messages to keep
            max_history_items: Max history items to include in context
        """
        self.task = task
        self.max_history_items = max_history_items
        
        # Set up message history
        self._history = MessageHistory(max_messages=max_history_messages)
        
        # Set system message
        if system_prompt is None:
            system_prompt = SystemPrompt()
        self._history.set_system_message(system_prompt.get_message())
        
        # Track state
        self._step_count = 0
        self._last_screenshot: Optional[str] = None
    
    def build_step_message(
        self,
        browser_state: "BrowserState",
        agent_history: "AgentHistoryList",
        step_info: Dict[str, Any],
        include_screenshot: bool = True,
    ) -> List[Message]:
        """
        Build messages for a single step.
        
        Args:
            browser_state: Current browser state
            agent_history: Agent's history
            step_info: Current step information
            include_screenshot: Whether to include screenshot
            
        Returns:
            List of messages for the LLM
        """
        # Build history description
        history_desc = agent_history.get_history_description(
            max_items=self.max_history_items
        )
        
        # Build user message
        user_message = build_user_message(
            browser_state=browser_state,
            task=self.task,
            agent_history=history_desc,
            step_info=step_info,
            include_screenshot=include_screenshot and bool(browser_state.screenshot_b64),
        )
        
        # Add to history
        self._history.add(user_message)
        
        # Track screenshot
        if browser_state.screenshot_b64:
            self._last_screenshot = browser_state.screenshot_b64
        
        self._step_count += 1
        
        return self._history.get_messages()
    
    def add_assistant_response(self, response: str) -> None:
        """Add an assistant response to history."""
        self._history.add(AssistantMessage(content=response))
    
    def add_error_message(self, error: str) -> None:
        """Add an error message for retry."""
        error_msg = f"<error>\n{error}\n</error>\n\nPlease try again with a valid response."
        self._history.add(UserMessage(content=error_msg))
    
    def get_messages(self) -> List[Message]:
        """Get all messages."""
        return self._history.get_messages()
    
    def get_openai_messages(self) -> List[Dict[str, Any]]:
        """Get messages in OpenAI API format."""
        return self._history.to_openai_format()
    
    def clear(self) -> None:
        """Clear message history (keeps system message)."""
        self._history.clear()
        self._step_count = 0
    
    @property
    def step_count(self) -> int:
        """Get current step count."""
        return self._step_count
    
    @property
    def message_count(self) -> int:
        """Get total message count."""
        return len(self._history)


class CompactMessageManager(MessageManager):
    """
    Message manager that keeps conversation history compact.
    
    Instead of keeping full conversation, it maintains only:
    - System message
    - Current state message
    - Summarized history in the state
    """
    
    def build_step_message(
        self,
        browser_state: "BrowserState",
        agent_history: "AgentHistoryList",
        step_info: Dict[str, Any],
        include_screenshot: bool = True,
    ) -> List[Message]:
        """
        Build messages with minimal history.
        
        This version creates fresh messages each step instead
        of accumulating conversation history.
        """
        # Clear previous user messages (keep system)
        self._history.clear()
        
        # Build history description with limit
        history_desc = agent_history.get_history_description(
            max_items=self.max_history_items or 10
        )
        
        # Build user message
        user_message = build_user_message(
            browser_state=browser_state,
            task=self.task,
            agent_history=history_desc,
            step_info=step_info,
            include_screenshot=include_screenshot and bool(browser_state.screenshot_b64),
        )
        
        self._history.add(user_message)
        self._step_count += 1
        
        return self._history.get_messages()


def create_message_manager(
    task: str,
    compact: bool = True,
    **kwargs
) -> MessageManager:
    """
    Create an appropriate message manager.
    
    Args:
        task: The user's task
        compact: Use compact mode (recommended)
        **kwargs: Additional arguments for MessageManager
        
    Returns:
        MessageManager instance
    """
    if compact:
        return CompactMessageManager(task=task, **kwargs)
    return MessageManager(task=task, **kwargs)

