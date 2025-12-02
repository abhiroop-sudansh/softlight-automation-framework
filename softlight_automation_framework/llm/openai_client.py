"""OpenAI GPT client for LLM operations."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI
from pydantic import BaseModel

from softlight_automation_framework.core.config import LLMConfig
from softlight_automation_framework.core.exceptions import (
    LLMError,
    LLMResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from softlight_automation_framework.llm.messages import (
    Message,
    MessageHistory,
)
from softlight_automation_framework.llm.schema import (
    LLMResponse,
    AgentOutput,
)

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    OpenAI GPT client for browser automation.
    
    Handles:
    - Chat completions with structured output
    - Vision (image) inputs
    - Response parsing and validation
    - Rate limiting and retries
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout: int = 60,
        config: Optional[LLMConfig] = None,
    ):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key (uses env if not provided)
            model: Model name (e.g., "gpt-4o", "gpt-4o-mini")
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            config: LLMConfig object (overrides other params)
        """
        if config:
            self.config = config
        else:
            self.config = LLMConfig(
                api_key=api_key or "",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        
        # Initialize async client
        self._client = AsyncOpenAI(
            api_key=self.config.api_key or None,  # Uses OPENAI_API_KEY env if None
            timeout=self.config.timeout,
        )
        
        # Stats tracking
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_requests = 0
    
    @property
    def model(self) -> str:
        """Get the model name."""
        return self.config.model
    
    async def complete(
        self,
        messages: Union[List[Message], MessageHistory, List[Dict[str, Any]]],
        response_format: Optional[Type[BaseModel]] = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of messages or MessageHistory
            response_format: Pydantic model for structured output
            max_retries: Number of retries on failure
            
        Returns:
            LLMResponse with content and usage stats
        """
        # Convert messages to API format
        if isinstance(messages, MessageHistory):
            api_messages = messages.to_openai_format()
        elif messages and isinstance(messages[0], Message):
            api_messages = [m.to_openai_format() for m in messages]
        else:
            api_messages = messages
        
        # Prepare request parameters
        params: Dict[str, Any] = {
            "model": self.config.model,
            "messages": api_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        # Add response format for structured output
        if response_format:
            # Use simple JSON mode instead of strict schema (more compatible)
            params["response_format"] = {"type": "json_object"}
        
        # Make request with retries
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(**params),
                    timeout=self.config.timeout
                )
                
                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Extract response data
                choice = response.choices[0]
                content = choice.message.content or ""
                
                # Parse structured output if expected
                parsed = None
                if response_format and content:
                    try:
                        data = json.loads(content)
                        parsed = response_format(**data)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Failed to parse structured output: {e}")
                
                # Update stats
                usage = response.usage
                if usage:
                    self._total_prompt_tokens += usage.prompt_tokens
                    self._total_completion_tokens += usage.completion_tokens
                self._total_requests += 1
                
                logger.debug(
                    f"LLM response: {usage.prompt_tokens if usage else 0} prompt, "
                    f"{usage.completion_tokens if usage else 0} completion tokens, "
                    f"{latency_ms}ms"
                )
                
                return LLMResponse(
                    content=content,
                    parsed=parsed if isinstance(parsed, AgentOutput) else None,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                    latency_ms=latency_ms,
                    model=response.model,
                    finish_reason=choice.finish_reason or "stop",
                )
                
            except asyncio.TimeoutError:
                last_error = LLMTimeoutError(self.config.timeout)
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{max_retries})")
                
            except Exception as e:
                error_str = str(e).lower()
                
                if "rate_limit" in error_str or "429" in error_str:
                    last_error = LLMRateLimitError()
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limit hit, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    last_error = LLMError(str(e), model=self.config.model)
                    logger.error(f"LLM error (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Wait before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
        
        raise last_error or LLMError("Unknown LLM error")
    
    async def get_agent_output(
        self,
        messages: Union[List[Message], MessageHistory],
        action_model: Type[BaseModel],
        include_thinking: bool = True,
    ) -> AgentOutput:
        """
        Get structured agent output from the LLM.
        
        Args:
            messages: Conversation messages
            action_model: Pydantic model for action schema
            include_thinking: Include thinking field in output
            
        Returns:
            Parsed AgentOutput with actions
        """
        # Create output schema with action model
        output_schema = AgentOutput.with_action_schema(action_model)
        
        response = await self.complete(
            messages=messages,
            response_format=output_schema,
        )
        
        if not response.content:
            raise LLMResponseError("Empty response from LLM")
        
        try:
            data = json.loads(response.content)
            return output_schema(**data)
        except json.JSONDecodeError as e:
            raise LLMResponseError(
                f"Invalid JSON in LLM response: {e}",
                raw_response=response.content
            )
        except Exception as e:
            raise LLMResponseError(
                f"Failed to parse agent output: {e}",
                raw_response=response.content
            )
    
    async def simple_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Simple text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system message
            
        Returns:
            Response text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.complete(messages)
        return response.content
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get cumulative usage statistics."""
        return {
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "total_requests": self._total_requests,
        }
    
    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_requests = 0

