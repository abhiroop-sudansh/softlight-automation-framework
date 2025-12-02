"""Tool/Action registry for managing browser actions."""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, create_model

from softlight_automation_framework.tools.views import (
    ActionResult,
    ActionModel,
    ActionDefinition,
    NoParamsAction,
)
from softlight_automation_framework.core.exceptions import (
    ActionError,
    ActionNotFoundError,
    ActionValidationError,
)

logger = logging.getLogger(__name__)


def action(
    description: str = "",
    param_model: Optional[Type[BaseModel]] = None,
    requires_browser: bool = True,
    is_terminal: bool = False,
):
    """
    Decorator for registering actions.
    
    Args:
        description: Description of what the action does
        param_model: Pydantic model for action parameters
        requires_browser: Whether action needs browser session
        is_terminal: Whether action terminates the agent (like 'done')
        
    Usage:
        @action("Navigate to a URL")
        async def navigate(url: str, browser: BrowserSession):
            await browser.navigate(url)
            return ActionResult(extracted_content=f"Navigated to {url}")
    """
    def decorator(func: Callable):
        func._action_metadata = {
            "description": description,
            "param_model": param_model,
            "requires_browser": requires_browser,
            "is_terminal": is_terminal,
        }
        return func
    return decorator


class ToolRegistry:
    """
    Registry for browser actions.
    
    Manages action registration, validation, and execution.
    Provides dynamic ActionModel generation for LLM output parsing.
    """
    
    def __init__(self, exclude_actions: Optional[List[str]] = None):
        """
        Initialize the tool registry.
        
        Args:
            exclude_actions: List of action names to exclude
        """
        self._actions: Dict[str, ActionDefinition] = {}
        self._exclude_actions = set(exclude_actions or [])
        self._action_model: Optional[Type[ActionModel]] = None
    
    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        param_model: Optional[Type[BaseModel]] = None,
        requires_browser: bool = True,
        is_terminal: bool = False,
    ) -> None:
        """
        Register an action.
        
        Args:
            name: Action name
            handler: Async function to execute
            description: Human-readable description
            param_model: Pydantic model for parameters
            requires_browser: Whether browser session is required
            is_terminal: Whether this action ends the agent loop
        """
        if name in self._exclude_actions:
            logger.debug(f"Skipping excluded action: {name}")
            return
        
        # Generate param model from function signature if not provided
        if param_model is None:
            param_model = self._generate_param_model(name, handler)
        
        definition = ActionDefinition(
            name=name,
            description=description or f"Execute {name} action",
            param_model=param_model,
            handler=handler,
            requires_browser=requires_browser,
            is_terminal=is_terminal,
        )
        
        self._actions[name] = definition
        self._action_model = None  # Invalidate cached model
        
        logger.debug(f"Registered action: {name}")
    
    def _generate_param_model(
        self,
        name: str,
        handler: Callable
    ) -> Type[BaseModel]:
        """Generate a Pydantic model from function signature."""
        sig = inspect.signature(handler)
        fields = {}
        
        for param_name, param in sig.parameters.items():
            # Skip special parameters
            if param_name in ("self", "browser", "browser_session", "llm", "session"):
                continue
            
            # Get type annotation
            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                annotation = Any
            
            # Get default value
            default = param.default
            if default == inspect.Parameter.empty:
                default = ...  # Required field
            
            fields[param_name] = (annotation, default)
        
        if not fields:
            return NoParamsAction
        
        return create_model(f"{name.title()}Params", **fields)
    
    def action(
        self,
        description: str = "",
        param_model: Optional[Type[BaseModel]] = None,
        requires_browser: bool = True,
        is_terminal: bool = False,
    ):
        """
        Decorator for registering actions.
        
        Usage:
            @registry.action("Navigate to URL")
            async def navigate(params: NavigateParams, browser: BrowserSession):
                ...
        """
        def decorator(func: Callable):
            name = func.__name__
            self.register(
                name=name,
                handler=func,
                description=description,
                param_model=param_model,
                requires_browser=requires_browser,
                is_terminal=is_terminal,
            )
            return func
        return decorator
    
    def exclude_action(self, name: str) -> None:
        """Exclude an action from the registry."""
        self._exclude_actions.add(name)
        if name in self._actions:
            del self._actions[name]
            self._action_model = None
    
    def get_action(self, name: str) -> Optional[ActionDefinition]:
        """Get an action definition by name."""
        return self._actions.get(name)
    
    def get_all_actions(self) -> Dict[str, ActionDefinition]:
        """Get all registered actions."""
        return self._actions.copy()
    
    def get_action_names(self) -> List[str]:
        """Get list of all action names."""
        return list(self._actions.keys())
    
    def get_action_model(self) -> Type[ActionModel]:
        """
        Get the dynamic ActionModel class with all registered actions.
        
        Returns a Pydantic model where each action is an optional field.
        """
        if self._action_model is not None:
            return self._action_model
        
        fields = {}
        for name, definition in self._actions.items():
            fields[name] = (Optional[definition.param_model], None)
        
        self._action_model = create_model(
            "ActionModel",
            __base__=ActionModel,
            **fields
        )
        
        return self._action_model
    
    def get_actions_schema(self) -> List[Dict[str, Any]]:
        """Get JSON schema for all actions (for LLM function calling)."""
        schemas = []
        for definition in self._actions.values():
            schemas.append(definition.get_schema())
        return schemas
    
    def get_actions_description(self) -> str:
        """Get human-readable description of all actions."""
        lines = ["Available actions:"]
        for name, definition in self._actions.items():
            lines.append(f"  - {name}: {definition.description}")
        return "\n".join(lines)
    
    async def execute(
        self,
        action_name: str,
        params: Union[Dict[str, Any], BaseModel],
        browser_session: Optional[Any] = None,
        **context
    ) -> ActionResult:
        """
        Execute an action.
        
        Args:
            action_name: Name of the action to execute
            params: Action parameters (dict or Pydantic model)
            browser_session: Browser session (if required)
            **context: Additional context to pass to handler
            
        Returns:
            ActionResult from the action handler
        """
        definition = self._actions.get(action_name)
        if not definition:
            raise ActionNotFoundError(action_name)
        
        # Validate parameters
        if isinstance(params, dict):
            try:
                params = definition.param_model(**params)
            except Exception as e:
                raise ActionValidationError(action_name, str(e))
        
        # Build handler arguments
        handler_kwargs = {}
        sig = inspect.signature(definition.handler)
        
        for param_name, param in sig.parameters.items():
            if param_name == "params":
                handler_kwargs["params"] = params
            elif param_name in ("browser", "browser_session"):
                if definition.requires_browser and browser_session is None:
                    raise ActionError(
                        action_name,
                        "Browser session required but not provided"
                    )
                handler_kwargs[param_name] = browser_session
            elif param_name in context:
                handler_kwargs[param_name] = context[param_name]
            elif hasattr(params, param_name):
                handler_kwargs[param_name] = getattr(params, param_name)
        
        # Execute handler
        try:
            logger.debug(f"Executing action: {action_name}")
            
            result = definition.handler(**handler_kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            
            # Normalize result
            if result is None:
                return ActionResult()
            elif isinstance(result, ActionResult):
                return result
            elif isinstance(result, str):
                return ActionResult(extracted_content=result)
            elif isinstance(result, dict):
                return ActionResult(**result)
            else:
                return ActionResult(extracted_content=str(result))
                
        except Exception as e:
            logger.error(f"Action {action_name} failed: {e}")
            raise ActionError(action_name, str(e))
    
    async def execute_action_model(
        self,
        action_model: ActionModel,
        browser_session: Optional[Any] = None,
        **context
    ) -> ActionResult:
        """
        Execute an action from an ActionModel instance.
        
        Args:
            action_model: ActionModel with one action set
            browser_session: Browser session
            **context: Additional context
            
        Returns:
            ActionResult from the action
        """
        # Find the action that was specified
        for field_name, value in action_model:
            if value is not None:
                return await self.execute(
                    action_name=field_name,
                    params=value,
                    browser_session=browser_session,
                    **context
                )
        
        return ActionResult(error="No action specified")
    
    def __len__(self) -> int:
        """Get number of registered actions."""
        return len(self._actions)
    
    def __contains__(self, name: str) -> bool:
        """Check if an action is registered."""
        return name in self._actions
    
    def __iter__(self):
        """Iterate over action definitions."""
        return iter(self._actions.values())

