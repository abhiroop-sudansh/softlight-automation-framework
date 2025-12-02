"""Data models for actions and results."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field, create_model, model_validator
from enum import Enum


class ActionResult(BaseModel):
    """Result of executing an action."""
    
    # Task completion
    is_done: bool = Field(default=False, description="Task is complete")
    success: Optional[bool] = Field(default=None, description="Task completed successfully")
    
    # Content
    extracted_content: Optional[str] = Field(default=None, description="Content extracted by the action")
    long_term_memory: Optional[str] = Field(default=None, description="Information to remember")
    
    # Error handling
    error: Optional[str] = Field(default=None, description="Error message if action failed")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional action metadata")
    
    # Files
    attachments: Optional[List[str]] = Field(default=None, description="File paths to attach")
    
    # Flags
    include_screenshot: bool = Field(default=False, description="Include screenshot in next observation")
    
    @model_validator(mode='after')
    def validate_success_requires_done(self):
        """Ensure success=True can only be set when is_done=True."""
        if self.success is True and self.is_done is not True:
            raise ValueError(
                'success=True can only be set when is_done=True. '
                'For regular actions that succeed, leave success as None.'
            )
        return self
    
    @property
    def has_error(self) -> bool:
        """Check if action resulted in an error."""
        return self.error is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return self.model_dump(exclude_none=True)


# Base action parameter models

class NoParamsAction(BaseModel):
    """Action that requires no parameters."""
    pass


class NavigateActionParams(BaseModel):
    """Parameters for navigate action."""
    url: str = Field(description="URL to navigate to")
    new_tab: bool = Field(default=False, description="Open in new tab")


class SearchActionParams(BaseModel):
    """Parameters for search action."""
    query: str = Field(description="Search query")
    engine: str = Field(default="google", description="Search engine (google, bing, duckduckgo)")


class ClickActionParams(BaseModel):
    """Parameters for click action."""
    index: Optional[int] = Field(default=None, description="Element index to click")
    coordinate_x: Optional[int] = Field(default=None, description="X coordinate to click")
    coordinate_y: Optional[int] = Field(default=None, description="Y coordinate to click")
    force: bool = Field(default=False, description="Force click even if obscured")
    
    @model_validator(mode='after')
    def validate_target(self):
        """Ensure either index or coordinates are provided."""
        if self.index is None and (self.coordinate_x is None or self.coordinate_y is None):
            raise ValueError("Must provide either index or both coordinate_x and coordinate_y")
        return self


class InputActionParams(BaseModel):
    """Parameters for input/type action."""
    index: int = Field(description="Element index to type into")
    text: str = Field(description="Text to type")
    clear: bool = Field(default=True, description="Clear existing content first")


class ScrollActionParams(BaseModel):
    """Parameters for scroll action."""
    down: bool = Field(default=True, description="Scroll down (True) or up (False)")
    pages: float = Field(default=1.0, description="Number of pages to scroll")
    index: Optional[int] = Field(default=None, description="Element index to scroll (None for page)")


class WaitActionParams(BaseModel):
    """Parameters for wait action."""
    seconds: float = Field(default=3.0, description="Seconds to wait", ge=0, le=30)


class ExtractActionParams(BaseModel):
    """Parameters for extract action."""
    query: str = Field(description="What information to extract")
    extract_links: bool = Field(default=False, description="Include URLs in extraction")


class DoneActionParams(BaseModel):
    """Parameters for done action."""
    text: str = Field(description="Final result/message to user")
    success: bool = Field(default=True, description="Whether task completed successfully")
    files_to_display: Optional[List[str]] = Field(default=None, description="Files to attach")


class SendKeysActionParams(BaseModel):
    """Parameters for send_keys action."""
    keys: str = Field(description="Keys to send (e.g., 'Enter', 'Tab Tab ArrowDown')")


class SwitchTabActionParams(BaseModel):
    """Parameters for switch_tab action."""
    tab_id: str = Field(description="Tab ID to switch to (last 4 chars)")


class CloseTabActionParams(BaseModel):
    """Parameters for close_tab action."""
    tab_id: str = Field(description="Tab ID to close (last 4 chars)")


class DropdownOptionsActionParams(BaseModel):
    """Parameters for dropdown_options action."""
    index: int = Field(description="Dropdown element index")


class SelectDropdownActionParams(BaseModel):
    """Parameters for select_dropdown action."""
    index: int = Field(description="Dropdown element index")
    text: str = Field(description="Option text to select")


class UploadFileActionParams(BaseModel):
    """Parameters for upload_file action."""
    index: int = Field(description="File input element index")
    path: str = Field(description="Path to file to upload")


class EvaluateActionParams(BaseModel):
    """Parameters for evaluate (JavaScript) action."""
    code: str = Field(description="JavaScript code to execute")


@dataclass
class ActionDefinition:
    """Definition of a registered action."""
    
    name: str
    description: str
    param_model: Type[BaseModel]
    handler: Callable
    
    # Metadata
    requires_browser: bool = True
    is_terminal: bool = False  # True for 'done' action
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this action."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.param_model.model_json_schema(),
        }


class ActionModel(BaseModel):
    """
    Dynamic model for agent actions.
    
    This model is dynamically extended with registered actions,
    allowing the agent to output structured action calls.
    """
    
    model_config = {"extra": "forbid"}
    
    def get_action_name(self) -> Optional[str]:
        """Get the name of the action being performed."""
        for field_name, value in self:
            if value is not None:
                return field_name
        return None
    
    def get_action_params(self) -> Optional[BaseModel]:
        """Get the parameters of the action being performed."""
        for field_name, value in self:
            if value is not None:
                return value
        return None
    
    def get_index(self) -> Optional[int]:
        """Get element index if the action has one."""
        params = self.get_action_params()
        if params and hasattr(params, "index"):
            return params.index
        return None
    
    @classmethod
    def create_with_actions(
        cls,
        actions: Dict[str, Type[BaseModel]]
    ) -> Type["ActionModel"]:
        """
        Create a new ActionModel class with the given actions.
        
        Args:
            actions: Dict mapping action names to param models
            
        Returns:
            New ActionModel class with action fields
        """
        fields = {}
        for name, param_model in actions.items():
            fields[name] = (Optional[param_model], None)
        
        return create_model(
            "ActionModel",
            __base__=cls,
            **fields
        )


# Pre-defined action aliases for convenience
NavigateAction = NavigateActionParams
ClickAction = ClickActionParams
InputAction = InputActionParams
ScrollAction = ScrollActionParams
WaitAction = WaitActionParams
ExtractAction = ExtractActionParams
DoneAction = DoneActionParams
SendKeysAction = SendKeysActionParams
SwitchTabAction = SwitchTabActionParams
CloseTabAction = CloseTabActionParams

