"""Main agent executor - the core agent implementation."""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from softlight_automation_framework.core.config import AgentConfig, Config
from softlight_automation_framework.core.exceptions import (
    AgentError,
    MaxStepsReachedError,
    MaxFailuresReachedError,
    LLMResponseError,
)
from softlight_automation_framework.browser.session import BrowserSession
from softlight_automation_framework.tools.registry import ToolRegistry
from softlight_automation_framework.tools.actions import create_default_registry
from softlight_automation_framework.tools.views import ActionResult, ActionModel
from softlight_automation_framework.llm.openai_client import OpenAIClient
from softlight_automation_framework.llm.schema import AgentOutput
from softlight_automation_framework.agent.prompts import SystemPrompt
from softlight_automation_framework.agent.message_manager import (
    MessageManager,
    create_message_manager,
)
from softlight_automation_framework.agent.views import (
    AgentState,
    AgentSettings,
    AgentHistory,
    AgentHistoryList,
    AgentStepInfo,
    StepMetadata,
)

logger = logging.getLogger(__name__)


class Agent:
    """
    Main agent class for browser automation.
    
    The agent operates in a loop:
    1. Get current browser state
    2. Build prompt with state and history
    3. Get LLM decision (actions to take)
    4. Execute actions
    5. Record results
    6. Repeat until done or max steps reached
    
    Usage:
        async with BrowserSession() as browser:
            agent = Agent(
                task="Search for Python tutorials on Google",
                llm=OpenAIClient(),
                browser=browser,
            )
            result = await agent.run()
    """
    
    def __init__(
        self,
        task: str,
        llm: OpenAIClient,
        browser: BrowserSession,
        tools: Optional[ToolRegistry] = None,
        settings: Optional[AgentSettings] = None,
        # Convenience parameters (override settings)
        max_steps: int = 100,
        max_actions_per_step: int = 4,
        max_failures: int = 3,
        use_vision: bool = True,
        override_system_message: Optional[str] = None,
        extend_system_message: Optional[str] = None,
        output_model: Optional[Type[BaseModel]] = None,
    ):
        """
        Initialize the agent.
        
        Args:
            task: The task to accomplish
            llm: LLM client for decision making
            browser: Browser session for web interaction
            tools: Tool registry (uses default if not provided)
            settings: Agent settings
            max_steps: Maximum steps allowed
            max_actions_per_step: Maximum actions per step
            max_failures: Maximum consecutive failures
            use_vision: Include screenshots in prompts
            override_system_message: Replace default system prompt
            extend_system_message: Append to system prompt
            output_model: Structured output model for done action
        """
        self.task = task
        self.llm = llm
        self.browser = browser
        
        # Settings
        if settings:
            self.settings = settings
        else:
            self.settings = AgentSettings(
                max_steps=max_steps,
                max_actions_per_step=max_actions_per_step,
                max_failures=max_failures,
                use_vision=use_vision,
                override_system_message=override_system_message,
                extend_system_message=extend_system_message,
            )
        
        # Tools
        self.tools = tools or create_default_registry()
        self._action_model = self.tools.get_action_model()
        
        # State
        self.state = AgentState()
        self.history = AgentHistoryList()
        
        # Message management
        self._system_prompt = SystemPrompt(
            max_actions_per_step=self.settings.max_actions_per_step,
            override_system_message=self.settings.override_system_message,
            extend_system_message=self.settings.extend_system_message,
            use_thinking=self.settings.use_thinking,
        )
        self._message_manager = create_message_manager(
            task=task,
            system_prompt=self._system_prompt,
            compact=True,
        )
        
        # Output model for structured output
        self._output_model = output_model
        
        logger.info(f"Agent initialized for task: {task[:100]}...")
    
    async def run(
        self,
        max_steps: Optional[int] = None,
    ) -> AgentHistoryList:
        """
        Run the agent until completion or max steps.
        
        Args:
            max_steps: Override max steps setting
            
        Returns:
            AgentHistoryList with full execution history
        """
        max_steps = max_steps or self.settings.max_steps
        
        self.state.start_time = datetime.now()
        self.state.n_steps = 0
        
        logger.info(f"Starting agent run (max_steps={max_steps})")
        
        try:
            while not self.state.is_done and self.state.n_steps < max_steps:
                # Check for stop signal
                if self.state.is_stopped:
                    logger.info("Agent stopped by user")
                    break
                
                # Handle pause
                while self.state.is_paused:
                    await asyncio.sleep(0.1)
                
                # Execute one step
                try:
                    await self._execute_step()
                except Exception as e:
                    logger.error(f"Step {self.state.n_steps} failed: {e}")
                    self.state.consecutive_failures += 1
                    
                    if self.state.consecutive_failures >= self.settings.max_failures:
                        raise MaxFailuresReachedError(self.settings.max_failures)
                
                self.state.n_steps += 1
            
            # Check if we hit max steps without completing
            if self.state.n_steps >= max_steps and not self.state.is_done:
                logger.warning(f"Agent reached max steps ({max_steps})")
                # Try to get a final response
                await self._force_completion()
        
        finally:
            self.state.end_time = datetime.now()
            
            duration = (self.state.end_time - self.state.start_time).total_seconds()
            logger.info(
                f"Agent run completed: {self.state.n_steps} steps, "
                f"{duration:.1f}s, success={self.state.success}"
            )
        
        return self.history
    
    async def _execute_step(self) -> None:
        """Execute a single agent step."""
        step_start = time.time()
        step_number = self.state.n_steps
        
        logger.debug(f"Executing step {step_number}")
        
        # Get current browser state
        browser_state = await self.browser.get_state(force_refresh=True)
        
        # Build step info
        step_info = AgentStepInfo(
            step_number=step_number,
            max_steps=self.settings.max_steps,
        )
        
        # Build messages for LLM
        messages = self._message_manager.build_step_message(
            browser_state=browser_state,
            agent_history=self.history,
            step_info=step_info.to_dict(),
            include_screenshot=self.settings.use_vision,
        )
        
        # Get LLM response
        try:
            response = await self.llm.complete(
                messages=messages,
                response_format=self._get_output_schema(),
            )
            
            # Add response to message history
            self._message_manager.add_assistant_response(response.content)
            
            # Parse output
            agent_output = self._parse_response(response.content)
            
        except LLMResponseError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            self._message_manager.add_error_message(str(e))
            raise
        
        # Execute actions
        results = await self._execute_actions(agent_output.action)
        
        # Create history entry
        step_end = time.time()
        history_entry = AgentHistory(
            model_output=agent_output,
            results=results,
            url=browser_state.url,
            title=browser_state.title,
            screenshot_b64=browser_state.screenshot_b64,
            screenshot_path=browser_state.screenshot_path,
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
        
        # Log step summary
        action_names = [list(a.keys())[0] for a in agent_output.action if a]
        logger.info(
            f"Step {step_number}: {', '.join(action_names)} "
            f"({step_end - step_start:.1f}s)"
        )
    
    def _get_output_schema(self) -> Type[BaseModel]:
        """Get the output schema for LLM response."""
        # Create schema with action model
        return AgentOutput.with_action_schema(self._action_model)
    
    def _parse_response(self, content: str) -> AgentOutput:
        """Parse LLM response into AgentOutput."""
        try:
            data = json.loads(content)
            
            # Parse actions
            actions = data.get("action", [])
            if not actions:
                raise ValueError("No actions in response")
            
            # Validate actions against action model
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
            raise LLMResponseError(
                f"Invalid JSON: {e}",
                raw_response=content
            )
        except Exception as e:
            raise LLMResponseError(
                f"Failed to parse response: {e}",
                raw_response=content
            )
    
    async def _execute_actions(
        self,
        actions: List[Dict[str, Any]],
    ) -> List[ActionResult]:
        """Execute a list of actions."""
        results = []
        
        for action in actions[:self.settings.max_actions_per_step]:
            try:
                # Get action name and params
                if not action:
                    continue
                
                action_name = list(action.keys())[0]
                params = action[action_name]
                
                logger.debug(f"Executing action: {action_name}")
                
                # Execute via registry
                result = await self.tools.execute(
                    action_name=action_name,
                    params=params,
                    browser_session=self.browser,
                    llm=self.llm,
                )
                
                results.append(result)
                
                # Stop on error or done
                if result.error or result.is_done:
                    break
                
                # Refresh browser state after action
                await self.browser.get_state(force_refresh=True)
                
            except Exception as e:
                logger.error(f"Action failed: {e}")
                results.append(ActionResult(error=str(e)))
                break
        
        return results if results else [ActionResult()]
    
    async def _force_completion(self) -> None:
        """Force agent to complete when max steps reached."""
        logger.info("Forcing completion due to max steps")
        
        # Get final state
        browser_state = await self.browser.get_state()
        
        # Create done result with partial results
        final_result = self.history.final_result() or "Task incomplete - max steps reached"
        
        done_result = ActionResult(
            is_done=True,
            success=False,
            extracted_content=final_result,
            long_term_memory="Task incomplete due to step limit",
        )
        
        # Add to history
        self.history.add(AgentHistory(
            results=[done_result],
            url=browser_state.url,
            title=browser_state.title,
        ))
        
        self.state.is_done = True
        self.state.success = False
    
    # Control methods
    
    def pause(self) -> None:
        """Pause the agent."""
        self.state.is_paused = True
        logger.info("Agent paused")
    
    def resume(self) -> None:
        """Resume the agent."""
        self.state.is_paused = False
        logger.info("Agent resumed")
    
    def stop(self) -> None:
        """Stop the agent."""
        self.state.is_stopped = True
        logger.info("Agent stop requested")
    
    # Status methods
    
    @property
    def is_done(self) -> bool:
        """Check if agent is done."""
        return self.state.is_done
    
    @property
    def is_successful(self) -> Optional[bool]:
        """Check if agent succeeded (None if not done)."""
        if self.state.is_done:
            return self.state.success
        return None
    
    @property
    def current_step(self) -> int:
        """Get current step number."""
        return self.state.n_steps
    
    def get_result(self) -> Optional[str]:
        """Get the final result."""
        return self.history.final_result()
    
    def get_history(self) -> AgentHistoryList:
        """Get the full history."""
        return self.history


async def run_agent(
    task: str,
    model: str = "gpt-4o",
    headless: bool = False,
    max_steps: int = 20,
    **kwargs
) -> AgentHistoryList:
    """
    Convenience function to run an agent.
    
    Args:
        task: Task to accomplish
        model: LLM model to use
        headless: Run browser in headless mode
        max_steps: Maximum steps
        **kwargs: Additional arguments for Agent
        
    Returns:
        AgentHistoryList with results
    """
    llm = OpenAIClient(model=model)
    
    async with BrowserSession(headless=headless) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=max_steps,
            **kwargs
        )
        return await agent.run()

