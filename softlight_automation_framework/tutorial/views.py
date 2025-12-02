"""Data models for tutorial/workflow capture system."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UIState(BaseModel):
    """Represents a captured UI state during workflow execution."""
    
    step_number: int = Field(description="Step number in the workflow")
    timestamp: datetime = Field(default_factory=datetime.now)
    url: str = Field(description="Current page URL")
    title: str = Field(description="Page title")
    screenshot_path: str = Field(description="Path to saved screenshot")
    screenshot_b64: Optional[str] = Field(default=None, description="Base64 screenshot")
    
    # What happened at this step
    action_taken: str = Field(description="Description of the action taken")
    action_type: str = Field(description="Type of action (click, type, navigate, etc.)")
    
    # Element information if applicable
    element_description: Optional[str] = Field(default=None, description="Description of interacted element")
    element_index: Optional[int] = Field(default=None, description="Index of element clicked/typed into")
    
    # Agent reasoning
    agent_thinking: Optional[str] = Field(default=None, description="Agent's reasoning for this step")
    next_goal: Optional[str] = Field(default=None, description="Agent's next intended goal")
    
    # Annotations for tutorial
    annotation: Optional[str] = Field(default=None, description="Human-readable annotation for this step")
    highlight_region: Optional[Dict[str, int]] = Field(default=None, description="Region to highlight (x, y, w, h)")


class TutorialStep(BaseModel):
    """A single step in a tutorial workflow."""
    
    step_number: int
    instruction: str = Field(description="Human-readable instruction for this step")
    ui_state: UIState
    
    # Optional additional context
    tips: Optional[List[str]] = Field(default=None, description="Helpful tips for this step")
    warnings: Optional[List[str]] = Field(default=None, description="Warnings or common mistakes")
    
    def to_markdown(self) -> str:
        """Convert step to markdown format."""
        md = f"## Step {self.step_number}: {self.instruction}\n\n"
        md += f"![Step {self.step_number}]({self.ui_state.screenshot_path})\n\n"
        
        if self.ui_state.annotation:
            md += f"**Note:** {self.ui_state.annotation}\n\n"
        
        if self.tips:
            md += "**Tips:**\n"
            for tip in self.tips:
                md += f"- {tip}\n"
            md += "\n"
        
        if self.warnings:
            md += "**⚠️ Warnings:**\n"
            for warning in self.warnings:
                md += f"- {warning}\n"
            md += "\n"
        
        return md


class TutorialWorkflow(BaseModel):
    """Complete tutorial workflow for a task."""
    
    task_id: str = Field(description="Unique identifier for this task")
    task_name: str = Field(description="Sanitized task name for folder naming")
    original_query: str = Field(description="Original user query/request")
    app_name: str = Field(description="Name of the application (e.g., Linear, Notion)")
    app_url: str = Field(default="about:blank", description="Base URL of the application")
    
    # Workflow metadata
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)
    success: bool = Field(default=False)
    
    # Steps
    steps: List[TutorialStep] = Field(default_factory=list)
    
    # Output paths
    output_dir: str = Field(description="Directory where screenshots are saved")
    
    # Summary
    summary: Optional[str] = Field(default=None, description="Summary of the workflow")
    total_duration_seconds: Optional[float] = Field(default=None)
    
    def add_step(self, step: TutorialStep) -> None:
        """Add a step to the workflow."""
        self.steps.append(step)
    
    def complete(self, success: bool = True, summary: Optional[str] = None) -> None:
        """Mark workflow as complete."""
        self.completed_at = datetime.now()
        self.success = success
        self.summary = summary
        if self.created_at:
            self.total_duration_seconds = (self.completed_at - self.created_at).total_seconds()
    
    def to_markdown(self) -> str:
        """Export workflow as markdown tutorial."""
        md = f"# {self.original_query}\n\n"
        md += f"**Application:** {self.app_name}\n"
        md += f"**URL:** {self.app_url}\n"
        md += f"**Generated:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if self.summary:
            md += f"## Summary\n\n{self.summary}\n\n"
        
        md += "---\n\n"
        
        for step in self.steps:
            md += step.to_markdown()
            md += "---\n\n"
        
        if self.success:
            md += "✅ **Task completed successfully!**\n"
        else:
            md += "❌ **Task was not completed.**\n"
        
        return md
    
    def save_markdown(self, path: Optional[str] = None) -> str:
        """Save workflow as markdown file."""
        if path is None:
            path = str(Path(self.output_dir) / "tutorial.md")
        
        Path(path).write_text(self.to_markdown())
        return path
    
    def to_json_summary(self) -> Dict[str, Any]:
        """Export as JSON summary."""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "original_query": self.original_query,
            "app_name": self.app_name,
            "app_url": self.app_url,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "total_steps": len(self.steps),
            "duration_seconds": self.total_duration_seconds,
            "summary": self.summary,
            "steps": [
                {
                    "step_number": s.step_number,
                    "instruction": s.instruction,
                    "screenshot": s.ui_state.screenshot_path,
                    "url": s.ui_state.url,
                    "action": s.ui_state.action_taken,
                }
                for s in self.steps
            ],
        }


class TaskRequest(BaseModel):
    """Request from Agent A to perform a task."""
    
    query: str = Field(description="Natural language task request")
    app_hint: Optional[str] = Field(default=None, description="Optional hint about which app to use")
    start_url: Optional[str] = Field(default=None, description="Optional starting URL")
    
    # Constraints
    max_steps: int = Field(default=20, description="Maximum steps to attempt")
    capture_every_action: bool = Field(default=True, description="Capture screenshot after every action")
    
    @property
    def task_name(self) -> str:
        """Generate a sanitized task name for folder naming."""
        import re
        # Take first 50 chars, replace non-alphanumeric with underscore
        name = self.query[:50].lower()
        name = re.sub(r'[^a-z0-9]+', '_', name)
        name = name.strip('_')
        return name or "unnamed_task"

