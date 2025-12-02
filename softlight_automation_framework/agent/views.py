"""Data models for agent state and history."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from uuid import uuid4

from softlight_automation_framework.tools.views import ActionResult
from softlight_automation_framework.llm.schema import AgentOutput, AgentBrain


class AgentSettings(BaseModel):
    """Configuration settings for the agent."""
    
    use_vision: bool = Field(default=True, description="Include screenshots in prompts")
    max_actions_per_step: int = Field(default=4, description="Max actions per step")
    max_failures: int = Field(default=3, description="Max consecutive failures")
    max_steps: int = Field(default=100, description="Max total steps")
    step_timeout: int = Field(default=120, description="Timeout per step in seconds")
    use_thinking: bool = Field(default=True, description="Include thinking in output")
    override_system_message: Optional[str] = Field(default=None)
    extend_system_message: Optional[str] = Field(default=None)


class AgentState(BaseModel):
    """Current state of the agent."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Identity
    agent_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    
    # Progress
    n_steps: int = Field(default=0, description="Current step number")
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    
    # Results
    last_result: Optional[List[ActionResult]] = Field(default=None)
    last_output: Optional[AgentOutput] = Field(default=None)
    
    # Status
    is_done: bool = Field(default=False)
    is_paused: bool = Field(default=False)
    is_stopped: bool = Field(default=False)
    success: Optional[bool] = Field(default=None)
    
    # Timing
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)


@dataclass
class AgentStepInfo:
    """Information about the current step."""
    
    step_number: int
    max_steps: int
    
    @property
    def is_last_step(self) -> bool:
        """Check if this is the last allowed step."""
        return self.step_number >= self.max_steps - 1
    
    @property
    def remaining_steps(self) -> int:
        """Get number of remaining steps."""
        return max(0, self.max_steps - self.step_number - 1)
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "max_steps": self.max_steps,
        }


@dataclass
class StepMetadata:
    """Metadata for a single step."""
    
    step_number: int
    start_time: float
    end_time: float
    
    @property
    def duration_seconds(self) -> float:
        """Calculate step duration."""
        return self.end_time - self.start_time


@dataclass
class AgentHistory:
    """History item for a single step."""
    
    # Model output
    model_output: Optional[AgentOutput] = None
    
    # Results
    results: List[ActionResult] = field(default_factory=list)
    
    # Browser state
    url: Optional[str] = None
    title: Optional[str] = None
    screenshot_path: Optional[str] = None
    screenshot_b64: Optional[str] = None
    
    # Metadata
    metadata: Optional[StepMetadata] = None
    
    # Interacted elements
    interacted_elements: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_output": {
                "thinking": self.model_output.thinking if self.model_output else None,
                "evaluation": self.model_output.evaluation_previous_goal if self.model_output else None,
                "memory": self.model_output.memory if self.model_output else None,
                "next_goal": self.model_output.next_goal if self.model_output else None,
                "actions": self.model_output.action if self.model_output else [],
            } if self.model_output else None,
            "results": [r.to_dict() for r in self.results],
            "url": self.url,
            "title": self.title,
            "screenshot_path": self.screenshot_path,
            "metadata": {
                "step_number": self.metadata.step_number,
                "duration_seconds": self.metadata.duration_seconds,
            } if self.metadata else None,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary for history description."""
        summary = {
            "step_number": self.metadata.step_number if self.metadata else 0,
        }
        
        if self.model_output:
            summary["evaluation"] = self.model_output.evaluation_previous_goal
            summary["memory"] = self.model_output.memory
            summary["next_goal"] = self.model_output.next_goal
        
        # Add action summaries
        summary["actions"] = []
        if self.model_output:
            for action, result in zip(self.model_output.action, self.results):
                action_name = list(action.keys())[0] if action else "unknown"
                summary["actions"].append({
                    "name": action_name,
                    "result": result.extracted_content if result else None,
                    "error": result.error if result else None,
                })
        
        return summary


T = TypeVar("T", bound=BaseModel)


class AgentHistoryList(BaseModel, Generic[T]):
    """List of agent history items."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    history: List[AgentHistory] = Field(default_factory=list)
    
    # Output schema for structured output
    _output_schema: Optional[type] = None
    
    def add(self, item: AgentHistory) -> None:
        """Add a history item."""
        self.history.append(item)
    
    def __len__(self) -> int:
        """Get number of history items."""
        return len(self.history)
    
    def __iter__(self):
        """Iterate over history items."""
        return iter(self.history)
    
    # Accessors
    
    def urls(self) -> List[Optional[str]]:
        """Get all URLs from history."""
        return [h.url for h in self.history]
    
    def screenshots(self) -> List[Optional[str]]:
        """Get all screenshots (base64) from history."""
        return [h.screenshot_b64 for h in self.history]
    
    def screenshot_paths(self) -> List[Optional[str]]:
        """Get all screenshot paths from history."""
        return [h.screenshot_path for h in self.history]
    
    def action_names(self) -> List[str]:
        """Get all action names from history."""
        names = []
        for h in self.history:
            if h.model_output:
                for action in h.model_output.action:
                    if action:
                        names.append(list(action.keys())[0])
        return names
    
    def errors(self) -> List[Optional[str]]:
        """Get all errors from history."""
        errors = []
        for h in self.history:
            step_errors = [r.error for r in h.results if r.error]
            errors.append(step_errors[0] if step_errors else None)
        return errors
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return any(e is not None for e in self.errors())
    
    def extracted_content(self) -> List[str]:
        """Get all extracted content from history."""
        content = []
        for h in self.history:
            for r in h.results:
                if r.extracted_content:
                    content.append(r.extracted_content)
        return content
    
    def final_result(self) -> Optional[str]:
        """Get the final extracted content."""
        if self.history:
            last = self.history[-1]
            if last.results:
                return last.results[-1].extracted_content
        return None
    
    def is_done(self) -> bool:
        """Check if agent completed."""
        if self.history:
            last = self.history[-1]
            if last.results:
                return last.results[-1].is_done or False
        return False
    
    def is_successful(self) -> Optional[bool]:
        """Check if agent succeeded (None if not done)."""
        if self.is_done() and self.history:
            last = self.history[-1]
            if last.results:
                return last.results[-1].success
        return None
    
    def total_duration_seconds(self) -> float:
        """Get total duration of all steps."""
        total = 0.0
        for h in self.history:
            if h.metadata:
                total += h.metadata.duration_seconds
        return total
    
    def number_of_steps(self) -> int:
        """Get number of steps."""
        return len(self.history)
    
    def model_thoughts(self) -> List[AgentBrain]:
        """Get all agent thoughts from history."""
        return [
            h.model_output.brain
            for h in self.history
            if h.model_output
        ]
    
    def action_results(self) -> List[ActionResult]:
        """Get all action results."""
        results = []
        for h in self.history:
            results.extend(h.results)
        return results
    
    def get_history_description(self, max_items: Optional[int] = None) -> str:
        """Get formatted history for prompt context."""
        items = self.history
        if max_items:
            items = items[-max_items:]
        
        lines = []
        for h in items:
            summary = h.get_summary()
            step_num = summary.get("step_number", 0)
            
            lines.append(f"<step_{step_num}>")
            
            if summary.get("evaluation"):
                lines.append(f"Evaluation: {summary['evaluation']}")
            if summary.get("memory"):
                lines.append(f"Memory: {summary['memory']}")
            if summary.get("next_goal"):
                lines.append(f"Goal: {summary['next_goal']}")
            
            for action in summary.get("actions", []):
                if action.get("error"):
                    lines.append(f"Action: {action['name']} -> Error: {action['error']}")
                elif action.get("result"):
                    result_preview = str(action['result'])[:100]
                    lines.append(f"Action: {action['name']} -> {result_preview}")
            
            lines.append(f"</step_{step_num}>")
        
        return "\n".join(lines) if lines else "No previous actions"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "history": [h.to_dict() for h in self.history],
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Save history to JSON file."""
        import json
        from pathlib import Path
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

