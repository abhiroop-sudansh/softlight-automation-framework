"""Workflow capture system for saving UI states during task execution."""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from softlight_automation_framework.tutorial.views import (
    UIState,
    TutorialStep,
    TutorialWorkflow,
    TaskRequest,
)

logger = logging.getLogger(__name__)


class WorkflowCapture:
    """
    Captures and saves UI states during workflow execution.
    
    Saves screenshots and metadata to datasets/<task_name>/ folder.
    """
    
    def __init__(
        self,
        base_dir: str = "./datasets",
        task_request: Optional[TaskRequest] = None,
    ):
        """
        Initialize workflow capture.
        
        Args:
            base_dir: Base directory for saving datasets
            task_request: The task request being executed
        """
        self.base_dir = Path(base_dir)
        self.task_request = task_request
        
        # Generate unique task ID
        self.task_id = str(uuid4())[:8]
        
        # Determine task name
        if task_request:
            self.task_name = task_request.task_name
            self.original_query = task_request.query
        else:
            self.task_name = f"task_{self.task_id}"
            self.original_query = ""
        
        # Create output directory
        self.output_dir = self.base_dir / self.task_name
        self.screenshots_dir = self.output_dir / "screenshots"
        
        self._ensure_directories()
        
        # Initialize workflow
        self.workflow: Optional[TutorialWorkflow] = None
        self._step_count = 0
        self._captured_states: List[UIState] = []
    
    def _ensure_directories(self) -> None:
        """Create necessary directories."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {self.output_dir}")
    
    def start_workflow(
        self,
        app_name: str,
        app_url: str,
    ) -> TutorialWorkflow:
        """
        Start a new workflow capture session.
        
        Args:
            app_name: Name of the application being used
            app_url: Base URL of the application
            
        Returns:
            New TutorialWorkflow instance
        """
        self.workflow = TutorialWorkflow(
            task_id=self.task_id,
            task_name=self.task_name,
            original_query=self.original_query,
            app_name=app_name,
            app_url=app_url,
            output_dir=str(self.output_dir),
        )
        
        self._step_count = 0
        self._captured_states = []
        
        logger.info(f"Started workflow capture: {self.task_name}")
        return self.workflow
    
    def capture_state(
        self,
        url: str,
        title: str,
        screenshot_b64: str,
        action_taken: str,
        action_type: str,
        element_description: Optional[str] = None,
        element_index: Optional[int] = None,
        agent_thinking: Optional[str] = None,
        next_goal: Optional[str] = None,
        annotation: Optional[str] = None,
    ) -> UIState:
        """
        Capture a UI state and save screenshot.
        
        Args:
            url: Current page URL
            title: Page title
            screenshot_b64: Base64 encoded screenshot
            action_taken: Description of action taken
            action_type: Type of action
            element_description: Description of element interacted with
            element_index: Index of element
            agent_thinking: Agent's reasoning
            next_goal: Agent's next goal
            annotation: Human-readable annotation
            
        Returns:
            Captured UIState
        """
        self._step_count += 1
        
        # Save screenshot
        screenshot_filename = f"step_{self._step_count:03d}.png"
        screenshot_path = self.screenshots_dir / screenshot_filename
        
        if screenshot_b64:
            screenshot_bytes = base64.b64decode(screenshot_b64)
            screenshot_path.write_bytes(screenshot_bytes)
            logger.debug(f"Saved screenshot: {screenshot_path}")
        
        # Create UI state
        ui_state = UIState(
            step_number=self._step_count,
            url=url,
            title=title,
            screenshot_path=str(screenshot_path.relative_to(self.output_dir)),
            action_taken=action_taken,
            action_type=action_type,
            element_description=element_description,
            element_index=element_index,
            agent_thinking=agent_thinking,
            next_goal=next_goal,
            annotation=annotation,
        )
        
        self._captured_states.append(ui_state)
        
        # Create and add tutorial step
        if self.workflow:
            instruction = self._generate_instruction(ui_state)
            step = TutorialStep(
                step_number=self._step_count,
                instruction=instruction,
                ui_state=ui_state,
            )
            self.workflow.add_step(step)
        
        logger.info(f"📸 Captured step {self._step_count}: {action_taken}")
        return ui_state
    
    def _generate_instruction(self, ui_state: UIState) -> str:
        """Generate human-readable instruction from UI state."""
        action = ui_state.action_type.lower()
        
        if action == "navigate":
            return f"Navigate to {ui_state.url}"
        elif action == "click":
            if ui_state.element_description:
                return f"Click on '{ui_state.element_description}'"
            elif ui_state.element_index is not None:
                return f"Click on element {ui_state.element_index}"
            return "Click on the element"
        elif action == "type" or action == "input":
            if ui_state.element_description:
                return f"Type in the '{ui_state.element_description}' field"
            return "Enter the required text"
        elif action == "scroll":
            return "Scroll the page to see more content"
        elif action == "extract":
            return "Review the information on screen"
        elif action == "done":
            return "Task completed"
        else:
            return ui_state.action_taken
    
    def complete_workflow(
        self,
        success: bool = True,
        summary: Optional[str] = None,
    ) -> TutorialWorkflow:
        """
        Complete the workflow capture session.
        
        Args:
            success: Whether the task was successful
            summary: Summary of the workflow
            
        Returns:
            Completed TutorialWorkflow
        """
        if not self.workflow:
            raise ValueError("No workflow started")
        
        self.workflow.complete(success=success, summary=summary)
        
        # Save workflow files
        self._save_workflow_files()
        
        logger.info(f"✅ Workflow complete: {self.task_name} (success={success})")
        return self.workflow
    
    def _save_workflow_files(self) -> None:
        """Save all workflow files."""
        if not self.workflow:
            return
        
        # Save markdown tutorial
        md_path = self.output_dir / "tutorial.md"
        md_path.write_text(self.workflow.to_markdown())
        logger.info(f"Saved tutorial: {md_path}")
        
        # Save JSON summary
        json_path = self.output_dir / "workflow.json"
        json_path.write_text(
            json.dumps(self.workflow.to_json_summary(), indent=2)
        )
        logger.info(f"Saved workflow JSON: {json_path}")
        
        # Save step-by-step metadata
        steps_path = self.output_dir / "steps.json"
        steps_data = [
            {
                "step": s.step_number,
                "instruction": s.instruction,
                "url": s.ui_state.url,
                "title": s.ui_state.title,
                "screenshot": s.ui_state.screenshot_path,
                "action_type": s.ui_state.action_type,
                "action_taken": s.ui_state.action_taken,
                "thinking": s.ui_state.agent_thinking,
            }
            for s in self.workflow.steps
        ]
        steps_path.write_text(json.dumps(steps_data, indent=2))
        logger.info(f"Saved steps metadata: {steps_path}")
    
    @property
    def step_count(self) -> int:
        """Get current step count."""
        return self._step_count
    
    @property
    def captured_states(self) -> List[UIState]:
        """Get all captured states."""
        return self._captured_states.copy()


def create_capture_session(
    query: str,
    base_dir: str = "./datasets",
    **kwargs
) -> WorkflowCapture:
    """
    Create a new capture session for a task.
    
    Args:
        query: Task query/request
        base_dir: Base directory for datasets
        **kwargs: Additional TaskRequest parameters
        
    Returns:
        Configured WorkflowCapture instance
    """
    request = TaskRequest(query=query, **kwargs)
    return WorkflowCapture(base_dir=base_dir, task_request=request)

