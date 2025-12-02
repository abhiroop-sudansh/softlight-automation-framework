"""Output schemas for LLM responses."""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field, create_model


class AgentBrain(BaseModel):
    """Agent's reasoning and planning state."""
    
    thinking: Optional[str] = Field(
        default=None,
        description="Internal reasoning process"
    )
    evaluation_previous_goal: str = Field(
        description="Assessment of last action's success/failure"
    )
    memory: str = Field(
        description="Key information to remember for future steps"
    )
    next_goal: str = Field(
        description="Immediate next goal to achieve"
    )


class AgentOutput(BaseModel):
    """Complete agent output including reasoning and actions."""
    
    thinking: Optional[str] = Field(
        default=None,
        description="Internal reasoning (optional)"
    )
    evaluation_previous_goal: Optional[str] = Field(
        default=None,
        description="Assessment of previous action"
    )
    memory: Optional[str] = Field(
        default=None,
        description="Information to remember"
    )
    next_goal: Optional[str] = Field(
        default=None,
        description="Next immediate goal"
    )
    action: List[Dict[str, Any]] = Field(
        description="List of actions to execute"
    )
    
    @property
    def brain(self) -> AgentBrain:
        """Get the agent's brain state."""
        return AgentBrain(
            thinking=self.thinking,
            evaluation_previous_goal=self.evaluation_previous_goal or "",
            memory=self.memory or "",
            next_goal=self.next_goal or "",
        )
    
    @classmethod
    def with_action_schema(
        cls,
        action_model: Type[BaseModel]
    ) -> Type["AgentOutput"]:
        """Create AgentOutput with specific action schema."""
        return create_model(
            "AgentOutput",
            __base__=cls,
            action=(
                List[action_model],
                Field(description="Actions to execute")
            )
        )


class LLMResponse(BaseModel):
    """Response from LLM API."""
    
    # Content
    content: str = Field(description="Response content")
    
    # Parsed output (if JSON mode)
    parsed: Optional[AgentOutput] = Field(
        default=None,
        description="Parsed agent output"
    )
    
    # Usage statistics
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    
    # Timing
    latency_ms: int = Field(default=0)
    
    # Model info
    model: str = Field(default="")
    finish_reason: str = Field(default="stop")
    
    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on token counts (rough approximation)."""
        # Rough pricing for GPT-4o (as of 2024)
        input_cost_per_1k = 0.005
        output_cost_per_1k = 0.015
        
        input_cost = (self.prompt_tokens / 1000) * input_cost_per_1k
        output_cost = (self.completion_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost


class StructuredOutput(BaseModel):
    """Base class for structured output models."""
    
    @classmethod
    def get_json_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for this output model."""
        return cls.model_json_schema()


def create_output_schema(
    name: str,
    fields: Dict[str, tuple],
    description: str = ""
) -> Type[StructuredOutput]:
    """
    Create a custom structured output schema.
    
    Args:
        name: Schema name
        fields: Dict of field_name -> (type, Field(...))
        description: Schema description
        
    Returns:
        New Pydantic model class
        
    Example:
        SearchResults = create_output_schema(
            "SearchResults",
            {
                "query": (str, Field(description="Search query")),
                "results": (List[str], Field(description="Search results")),
            }
        )
    """
    return create_model(
        name,
        __base__=StructuredOutput,
        **fields
    )

